"""Wrap an accepted compiler package in a persistent, one-slot SRAM mailbox.

No reference output is embedded: the real CPU executes the accepted RAW/CPU
kernels for every accepted request. Inputs and intermediate activations
are rewritten for each forward pass. This adds software only to the current RTL.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MAILBOX = 0x80001FC0
MAGIC = 0x4C495645
VERSION = 1
READY, BUSY, DONE, ERROR = 1, 2, 3, 4
BAD_COMMAND, BAD_LENGTH, COMPUTE_FAILURE = 1, 2, 3


@dataclass
class Resident:
    image: bytes
    program: object
    metadata: dict


def _source(package):
    """Accept an in-memory Package or a normal compiler deployment directory."""
    if isinstance(package, (str, Path)):
        directory = Path(package)
        metadata = json.loads((directory / 'manifest.json').read_text())
        image = (directory / 'firmware.bin').read_bytes()
    else:
        metadata = copy.deepcopy(package.metadata)
        image = bytes(package.memory.image)
    if len(image) != 8192 or metadata.get('target') != 'int22-raw-v1' or metadata.get('task_engine'):
        raise ValueError('Expected int22-raw-v1 compiler package and an exact 8KiB firmware image')
    if metadata.get('live_demo'):
        raise ValueError('Package is already resident; use the original compiler package')
    return metadata, bytearray(image)


def make_resident(package) -> Resident:
    # Import lazily so --help does not require the PyTorch compiler dependency.
    from compiler.compiler import Memory
    from compiler.codegen import Codegen
    from compiler.runtime import BASE

    metadata, image = _source(package)
    package_tag = hashlib.sha256(image).hexdigest()[:16]
    tensors = metadata['tensors']
    source = tensors[metadata['input']]
    output = tensors[metadata['output']]
    if source['shape'][0] != 1 or output['shape'][0] != 1:
        raise ValueError('Live demo currently supports batch=1')
    if not 1 <= output['shape'][1] <= 32:
        raise ValueError('Live classification output must have 1..32 INT8 elements')
    if source.get('storage') in ('internal', 'fused') or output.get('storage') in ('internal', 'fused'):
        raise ValueError('Input and final output must have public SRAM storage')
    for tensor in (source, output):
        address = tensor['address']
        if address < BASE or address + tensor['stride'] > MAILBOX or address % 4:
            raise ValueError('Tensor overlaps reserved mailbox or lies outside SRAM')

    memory = Memory()
    memory.image = image
    memory.allocations = copy.deepcopy(metadata['allocations'])
    memory.top = min(a['address'] - BASE for a in memory.allocations)
    memory.image[:metadata['code_bytes']] = bytes(metadata['code_bytes'])
    memory.image[MAILBOX-BASE:] = bytes(64)
    # No sample input or reference tensor is needed in the resident image.
    for name, tensor in tensors.items():
        if tensor.get('storage') not in ('internal', 'fused', 'special_fc', 'special_hidden'):
            at = tensor['address'] - BASE
            count = tensor['shape'][0] * tensor['stride']
            memory.image[at:at+count] = bytes(count)

    # RAW/CPU kernels use nearly all registers. Persistent request state must
    # live in a private allocation, never in x21..x24 across a kernel call.
    private = memory.alloc('live_request_state', 8, bytes(8))
    accumulator = next((entry['address'] for entry in memory.allocations
                        if entry['name']=='cpu_int32_accumulators'), 0)
    linears = [node for node in metadata['nodes'] if node['op']=='linear']
    has_raw = bool(metadata['npu_core_starts'])
    if metadata.get('batch_weight_reuse'):
        raise ValueError('Resident RAW demo supports batch=1, not batched kernel reuse')
    gen = Codegen(memory, tensors, accumulator, has_raw, single_raw=has_raw, batched_raw=False)
    a = gen.a
    # x21 is reloaded after every kernel; accepted sequence/cycle are in SRAM.
    a.li(21, MAILBOX)
    a.li(24, 0)
    a.li(5, -2)
    a.emit((0x320 << 20) | (5 << 15) | (1 << 12) | 0x73,
           'csrw mcountinhibit, x5 # enable mcycle, inhibit other counters')
    def put(offset, value):
        a.li(5, value)
        a.sw(5, 21, offset)
    put(0, MAGIC)
    put(4, VERSION)
    put(12, 0)
    put(28, 0)
    put(32, 0)
    put(36, 0)
    put(40, -1)
    put(44, output['shape'][1])
    put(48, source['address'])
    put(52, output['address'])
    put(56, int(package_tag, 16) & 0xffffffff)
    put(60, int(package_tag, 16) >> 32)
    a.emit(0x0ff0000f, 'fence iorw, iorw')
    put(24, READY)
    a.label('live_wait')
    a.lw(22, 21, 8)
    a.branch('beq', 22, 0, 'live_wait')
    a.lw(5, 21, 12)
    a.branch('beq', 22, 5, 'live_wait')
    a.emit(0x0ff0000f, 'fence iorw, iorw')
    a.rdcycle(23)
    a.li(6, private)
    a.sw(22, 6)
    a.sw(23, 6, 4)
    put(24, BUSY)
    put(28, 0)
    put(40, -1)
    a.lw(5, 21, 16)
    a.li(6, 1)
    # A compiler package can have a >4KiB CPU fallback body. Keep conditional
    # branches local and use JAL for the potentially distant error handlers.
    a.branch('beq', 5, 6, 'live_command_ok')
    a.jump('live_bad_command')
    a.label('live_command_ok')
    a.lw(5, 21, 20)
    a.li(6, source['shape'][1])
    a.branch('beq', 5, 6, 'live_length_ok')
    a.jump('live_bad_length')
    a.label('live_length_ok')
    a.lw(24, 21, 36)
    a.addi(24, 24, 1)
    a.sw(24, 21, 36)

    nodes = copy.deepcopy(metadata['nodes'])
    for node in nodes:
        node['start_pc'] = BASE + len(a.words)*4
        getattr(gen, 'linear' if node['op']=='linear' else
                'softmax' if node['op']=='softmax' else 'elementwise')(node)
        node['end_pc'] = BASE + len(a.words)*4
    a.li(21, MAILBOX)

    # Signed INT8 argmax of the actual output, with first-index tie breaking.
    a.li(5, output['address'])
    a.lb(6, 5)
    a.li(7, 0)
    for index in range(1, output['shape'][1]):
        a.lb(8, 5, index)
        skip = a.fresh('keep_argmax')
        a.branch('bge', 6, 8, skip)
        a.addi(6, 8, 0)
        a.li(7, index)
        a.label(skip)
    a.sw(7, 21, 40)
    put(24, DONE)
    a.jump('live_publish')
    a.label('live_bad_command')
    put(28, BAD_COMMAND)
    a.jump('live_error')
    a.label('live_bad_length')
    put(28, BAD_LENGTH)
    a.jump('live_error')
    a.label('fail')
    a.li(21, MAILBOX)
    put(28, COMPUTE_FAILURE)
    a.label('live_error')
    put(24, ERROR)
    a.label('live_publish')
    a.li(6, private)
    a.lw(22, 6)
    a.lw(23, 6, 4)
    a.rdcycle(5)
    a.sub(5, 5, 23)
    a.sw(5, 21, 32)
    # Successful result/error/cycle writes must all precede this commit word.
    a.emit(0x0ff0000f, 'fence iorw, iorw')
    a.sw(22, 21, 12)
    a.jump('live_wait')
    # The original finish() emits PASS/marker/halt. Instead keep its actual
    # shared matrix subroutines and return to the resident loop above.
    if linears:
        gen.matrix_runtime()
    a.resolve()
    code = struct.pack('<%dI' % len(a.words), *a.words)
    if len(code) > memory.top:
        raise ValueError(f'Resident code/data overlap: code {len(code)}B > available {memory.top}B')
    memory.image[:len(code)] = code
    metadata.update(nodes=nodes, allocations=memory.allocations, code_bytes=len(code), data_bytes=0x1fc0-memory.top, free_bytes=memory.top-len(code),
                    code_sha256=hashlib.sha256(code).hexdigest(), profile_ranges=[])
    metadata['live_demo'] = dict(
        abi=VERSION, backend='int22-raw-v1', private_state_address=private, mailbox_address=MAILBOX, input_address=source['address'],
        input_bytes=source['shape'][1], input_scale=source['scale'],
        output_address=output['address'], output_bytes=output['shape'][1],
        output_scale=output['scale'], clock_hz=20_000_000,
        scores_dtype='int8', magic=MAGIC, package_tag=package_tag,
        request_rule='One outstanding request; write input, command and input_bytes before nonzero request_seq',
        completion_rule='response_seq written last; output valid only with matching sequence, status DONE and error 0',
        error_recovery='Bad command/length may be followed by a new sequence; compute failure requires explicit reset/reload',
        cycle_scope='CPU acceptance to output/argmax publication; excludes USB/JTAG transfer, idle wait and final response commit',
    )
    return Resident(bytes(memory.image), a, metadata)


def write_resident(package, directory):
    resident = make_resident(package)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    words = struct.unpack('<2048I', resident.image)
    (directory / 'firmware.bin').write_bytes(resident.image)
    (directory / 'firmware.hex').write_text(''.join(f'{w:08x}\n' for w in words), newline='\n')
    (directory / 'firmware.S').write_text('\n'.join(resident.program.listing)+'\n', newline='\n')
    (directory / 'manifest.json').write_text(json.dumps(resident.metadata, indent=2)+'\n', newline='\n')
    return resident.metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True, help='Original compiler package directory')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.package.resolve() == args.out.resolve():
        parser.error('Use a separate output directory to preserve the original deployment package')
    metadata = write_resident(args.package, args.out)
    print(json.dumps(metadata['live_demo'], indent=2))


if __name__ == '__main__':
    main()
