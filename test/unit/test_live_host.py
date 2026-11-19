"""Host protocol/transport tests with explicitly fake memory and TCP peer.

These tests do not establish FPGA connectivity or numerical RTL correctness.
The corresponding real-CPU test is test/int8/run_live_demo.py.
"""
import json
from pathlib import Path
import re
import socket
import struct
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fpga.demo import protocol as p
from fpga.demo.host import DemoClient, DeviceError
from fpga.demo.transport import (BOOT_KEY, BOOT_STATUS, OpenOCDTransport, TransportError,
                                 read_bytes, write_bytes)


def metadata():
    return p.Metadata(0x80001E00, 5, 0.25, 0x80001E40, 3, 0.5,
                      package_tag="123456789abcdef0")


class FakeMemory:
    """Only a deterministic protocol peer, never an inference backend."""
    backend = "unit-test-memory-NOT-FPGA"

    def __init__(self, meta=None):
        self.meta = meta or metadata()
        self.memory = bytearray(p.SRAM_BYTES)
        self.writes = []
        self.execute_count = 0
        self.error = 0
        self.hold = False
        self.pending = None
        tag = int(self.meta.package_tag, 16)
        self.set_words(p.MAILBOX_BASE, [p.MAGIC, p.VERSION, 0, 0, 0, self.meta.input_bytes,
                                      p.READY, 0, 0, 0, 0, self.meta.output_bytes,
                                      self.meta.input_address, self.meta.output_address,
                                      tag & 0xffffffff, tag >> 32])

    def set_words(self, address, values):
        offset = address-p.SRAM_BASE
        self.memory[offset:offset+len(values)*4] = struct.pack(f"<{len(values)}I", *values)

    def read_words(self, address, count):
        if self.pending is not None and not self.hold:
            sequence = self.pending
            self.pending = None
            self.execute_count += 1
            self.memory[self.meta.output_address-p.SRAM_BASE:self.meta.output_address-p.SRAM_BASE+3] = bytes([0x80, 7, 4])
            self.set_words(p.MAILBOX_BASE+p.STATUS, [p.FAILED if self.error else p.DONE, self.error,
                                                   321, self.execute_count, 1])
            self.set_words(p.MAILBOX_BASE+p.RESPONSE_SEQ, [sequence])
        offset = address-p.SRAM_BASE
        return list(struct.unpack(f"<{count}I", self.memory[offset:offset+count*4]))

    def write_words(self, address, values):
        self.writes.append((address, list(values)))
        self.set_words(address, list(values))
        if address == p.MAILBOX_BASE+p.REQUEST_SEQ:
            response = struct.unpack_from("<I", self.memory, p.MAILBOX_BASE-p.SRAM_BASE+p.RESPONSE_SEQ)[0]
            if values[0] != response:
                self.pending = values[0]


class MailboxClientTests(unittest.TestCase):
    def test_repeated_requests_commit_last_and_return_actual_readback(self):
        peer = FakeMemory()
        client = DemoClient(peer, metadata()).attach()
        for sequence, values in enumerate(([1,2,3,4,5], [-128,127,0,-3,2], [0]*5), 1):
            result = client.infer(values)
            self.assertEqual(result.sequence, sequence)
            self.assertEqual(result.values, [-128,7,4])
            self.assertEqual(result.class_id, 1)
            self.assertEqual(result.cycles, 321)
            self.assertEqual(result.executions, sequence)
            self.assertIn("NOT-FPGA", result.backend)
            self.assertEqual(read_bytes(peer, metadata().input_address, 5), bytes(v&255 for v in values))
        self.assertEqual(peer.execute_count, 3)
        self.assertEqual([w[0] for w in peer.writes[-3:]],
                         [metadata().input_address, p.MAILBOX_BASE+p.COMMAND, p.MAILBOX_BASE+p.REQUEST_SEQ])

    def test_bad_input_never_writes_mailbox(self):
        peer = FakeMemory(); client = DemoClient(peer, metadata()).attach()
        for value in ([0]*4, [0]*4+[128], [0]*4+[1.5], [0]*4+[True]):
            with self.assertRaises(ValueError): client.infer(value)
        self.assertEqual(peer.writes, [])

    def test_input_tail_preserves_padding(self):
        peer = FakeMemory()
        peer.set_words(metadata().input_address, [0xDEADBEEF, 0xAABBCCDD])
        write_bytes(peer, metadata().input_address, bytes([1,2,3,4,5]))
        self.assertEqual(read_bytes(peer, metadata().input_address, 8), b"\x01\x02\x03\x04\x05\xcc\xbb\xaa")

    def test_timeout_reserves_slot_and_recovers_same_sequence(self):
        peer = FakeMemory(); peer.hold = True
        client = DemoClient(peer, metadata(), timeout=0.003, poll_interval=0.0001).attach()
        with self.assertRaises(TimeoutError): client.infer([1]*5)
        before = list(peer.writes)
        with self.assertRaisesRegex(RuntimeError, "pending"): client.infer([2]*5)
        self.assertEqual(peer.writes, before)
        peer.hold = False
        result = client.recover()
        self.assertEqual(result.sequence, 1)
        self.assertEqual(peer.execute_count, 1)

    def test_failed_response_does_not_return_previous_result(self):
        peer = FakeMemory(); client = DemoClient(peer, metadata()).attach()
        client.infer([1]*5)
        peer.error = 2
        with self.assertRaises(DeviceError) as cm: client.infer([2]*5)
        self.assertEqual((cm.exception.sequence, cm.exception.code), (2,2))
        peer.error = 0
        self.assertEqual(client.infer([3]*5).sequence, 3)

    def test_npu_failure_disables_client(self):
        peer = FakeMemory(); client = DemoClient(peer, metadata()).attach(); peer.error = 3
        with self.assertRaises(DeviceError): client.infer([2]*5)
        with self.assertRaisesRegex(RuntimeError, r"load\(\)"): client.infer([2]*5)
        with self.assertRaisesRegex(RuntimeError, "reset/reload"): client.attach()

    def test_wrong_package_rejected_even_same_shape(self):
        peer = FakeMemory()
        peer.set_words(p.MAILBOX_BASE+p.PACKAGE_TAG_LOW, [7])
        with self.assertRaisesRegex(RuntimeError, "package tag"):
            DemoClient(peer, metadata()).attach()

    def test_sequence_wrap_skips_zero(self):
        peer = FakeMemory()
        peer.set_words(p.MAILBOX_BASE+p.REQUEST_SEQ, [0xffffffff, 0xffffffff])
        result = DemoClient(peer, metadata()).attach().infer([0]*5)
        self.assertEqual(result.sequence, 1)

    def test_attach_does_not_overwrite_outstanding_request(self):
        peer = FakeMemory(); peer.set_words(p.MAILBOX_BASE+p.REQUEST_SEQ, [9,8])
        with self.assertRaisesRegex(RuntimeError, "outstanding"):
            DemoClient(peer, metadata()).attach()
        self.assertEqual(peer.writes, [])

    def test_quantization_matches_compiler_ties_and_saturation(self):
        client = DemoClient(FakeMemory(), metadata())
        self.assertEqual(client.quantize([0.125,0.375,-0.125,99,-99]), [0,2,0,127,-128])
        with self.assertRaises(ValueError): client.quantize([float('nan')]*5)


class TclPeer:
    """Local TCP simulator for framing tests; not an OpenOCD or FPGA process."""
    def __init__(self):
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0)); self.listener.listen(1)
        self.port = self.listener.getsockname()[1]
        self.commands = []
        self.memory = {}
        self.status = 0
        self.error = None
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        try:
            conn, _ = self.listener.accept()
            with conn:
                buffer = bytearray()
                while True:
                    data = conn.recv(65536)
                    if not data: break
                    buffer.extend(data)
                    while b'\x1a' in buffer:
                        end = buffer.index(0x1a); raw = bytes(buffer[:end]).decode()
                        del buffer[:end+1]
                        script = raw.split('catch {',1)[1].split('} __live_result',1)[0]
                        self.commands.append(script)
                        response = self.execute(script)
                        # Deliberately fragment every response before delimiter.
                        conn.sendall(response[:1].encode()); conn.sendall(response[1:].encode()+b'\x1a')
        except Exception as error:
            self.error = error
        finally:
            self.listener.close()

    def execute(self, script):
        if script == 'riscv mem_access sysbus': return '1 unknown command'
        if script == 'fail_for_test': return '1 deliberate test error'
        if script.startswith('read_memory'):
            _, address, _, count = script.split(); address, count = int(address,16), int(count)
            values = [self.status if address+4*i == BOOT_STATUS else self.memory.get(address+4*i, 0) for i in range(count)]
            return '0 ' + ' '.join(hex(v) for v in values)
        if script.startswith('write_memory'):
            match = re.fullmatch(r'write_memory (0x[0-9a-f]+) 32 \{([^}]+)\}', script)
            address = int(match[1],16); values = [int(v,16) for v in match[2].split()]
            for i, value in enumerate(values):
                at = address+4*i
                if at == BOOT_STATUS:
                    if value == BOOT_KEY and self.status == 2048: self.status |= 0x2000
                else:
                    self.memory[at] = value
                    if at == p.SRAM_BASE+self.status*4: self.status += 1
            return '0 '
        return '0 '


class TclTransportTests(unittest.TestCase):
    def test_fragmented_rpc_errors_memory_and_full_ordered_boot(self):
        peer = TclPeer()
        image = struct.pack('<2048I', *range(2048))
        with OpenOCDTransport('127.0.0.1', peer.port, timeout=2) as transport:
            self.assertIn('riscv set_mem_access sysbus', peer.commands)
            with self.assertRaises(TransportError): transport.command('fail_for_test')
            transport.boot_image(image)
            self.assertEqual(peer.status, 0x2800)
            self.assertEqual(transport.read_words(p.SRAM_BASE+8000, 2), [2000,2001])
            self.assertEqual(peer.commands[-2], 'resume')
            before = len(peer.commands)
            with self.assertRaisesRegex(TransportError, 'not empty'): transport.boot_image(image)
            self.assertFalse(any(command.startswith('halt') for command in peer.commands[before:]))
        peer.thread.join(2)
        self.assertIsNone(peer.error)

    def test_invalid_transport_access_rejected_before_socket(self):
        transport = OpenOCDTransport()
        with self.assertRaises(ValueError): transport.read_words(3,1)
        with self.assertRaises(ValueError): transport.write_words(0x80000000,[-1])
        with self.assertRaises(ValueError): transport.boot_image(b'bad-size')

    def test_close_interrupts_blocked_rpc_without_waiting_for_timeout(self):
        client, peer = socket.socketpair()
        client.settimeout(30)
        peer.settimeout(2)
        transport = OpenOCDTransport(timeout=30)
        transport._socket = client
        errors = []
        def request():
            try:
                transport.command('version')
            except Exception as error:
                errors.append(error)
        worker = threading.Thread(target=request, daemon=True)
        try:
            worker.start()
            self.assertTrue(peer.recv(4096))  # Peer intentionally never replies.
            transport.close()
            worker.join(2)
            self.assertFalse(worker.is_alive(), 'camera quit left a blocked RPC thread')
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], TransportError)
        finally:
            transport.close()
            peer.close()


if __name__ == '__main__':
    unittest.main()
