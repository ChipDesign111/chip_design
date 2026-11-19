"""Offline batch-controller and Tcl-transport checks; never connect to an FPGA."""
import copy
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import struct
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("firmware_batch",ROOT / "fpga/firmware_batch.py")
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


class BoardFixture:
    environment = "Offline control-flow fixture; not FPGA execution"

    def __init__(self, cases, fault=None):
        self.cases={c["firmware_sha256"]:c for c in cases}
        self.memory=bytearray(8192)
        struct.pack_into("<I",self.memory,0x1fe0,batch.PASS)
        self.fault=fault
        self.resets=self.resumes=0
        self.running=False
        self.log=None
        self.case=None
        self.boot=self.cycles=self.dpc=0
        self.mmio={}

    def preflight(self, timeout):
        pass

    def begin_log(self, path):
        self.log=path.open("w")

    def end_log(self):
        if self.log:
            self.log.close();self.log=None

    def reset_halt(self):
        self.resets+=1;self.boot=0;self.cycles=0;self.running=False
        self.dpc=0x10000;self.mmio={}
        if self.log:
            self.log.write("reset halt\n")

    def write_words(self, address, values):
        if address == batch.BOOT:
            if values == [0xb007c0de] and self.boot == 2048:
                self.boot=0x2800
            return
        for i,value in enumerate(values):
            offset=address-batch.BASE+i*4
            if not 0 <= offset <= 8188 or self.running:
                raise RuntimeError("invalid fixture write")
            struct.pack_into("<I",self.memory,offset,value)
            if offset == self.boot*4 and self.boot < 2048:
                self.boot+=1

    def load(self, image):
        words=struct.unpack("<2048I",image)
        self.write_words(batch.BASE,list(words[:2032] if self.fault == "partial_load" else words))

    def read_words(self, address, count):
        if address == batch.BOOT:
            return [self.boot]
        if address == batch.CYCLES:
            return [self.cycles]
        if batch.BASE <= address < batch.BASE+8192:
            return list(struct.unpack_from("<%dI" % count,self.memory,address-batch.BASE))
        return [self.mmio.get(address+i*4,0) for i in range(count)]

    def write_word(self, address, value):
        self.write_words(address,[value])

    def resume(self, address):
        if self.boot != 0x2800 or self.running or address != 0x10000:
            raise RuntimeError("reset/load/commit/explicit Boot ordering violated")
        self.resumes+=1;self.running=True
        self.case=self.cases[hashlib.sha256(self.memory).hexdigest()]
        self.dpc=self.case["halt_pc"]
        self.cycles=180232 if self.case["name"] == "raw_full_b4_cpu" else 12349
        for check in self.case["checks"]:
            value=check["expected"] | (~check["mask"] & 0xffffffff)
            if batch.BASE <= check["address"] < batch.BASE+8192:
                struct.pack_into("<I",self.memory,check["address"]-batch.BASE,value)
            else:
                self.mmio[check["address"]]=value
        struct.pack_into("<I",self.memory,0x1fe0,batch.PASS)
        if self.case["pair"]:
            struct.pack_into("<I",self.memory,0x1fc0,2)
        if self.case["npu_core_starts"]:
            values=dict(cycles=730,fc1_issue=128*self.case["npu_batch"],
                        fc2_issue=16*self.case["npu_batch"] if self.case["family"] == "har" else 0,
                        overlap_read=4,overlap_write=5,overlap_total=5)
            self.mmio.update({0x70000000+batch.COUNTERS[k]:v for k,v in values.items()})
        if self.fault == "first_two_samples_zero" and self.case["name"] == "raw_full_b4_cpu":
            self.memory[0x1e40:0x1e80]=bytes(64)
        if self.fault == "wrong_tag":
            struct.pack_into("<I",self.memory,0x1fe4,0)
        if self.fault == "incomplete":
            struct.pack_into("<I",self.memory,0x1fe0,0)
        if self.fault == "cpu_uses_npu":
            self.mmio[0x7000000c]=1
        if self.fault == "bad_overlap":
            self.mmio[0x7000001c]=0

    def wait(self, seconds):
        if self.fault == "interrupt":
            raise KeyboardInterrupt()

    def halt(self):
        self.running=False

    def pc(self):
        return self.dpc

    def cleanup(self):
        if self.running:
            self.halt()
        self.end_log()
        return []


class TclServer:
    """Local ephemeral TCP endpoint; emulate commands, fragment every response."""
    def __init__(self, board, error_command=None):
        self.board=board;self.error_command=error_command;self.commands=[]
        self.server=socket.socket()
        self.server.bind(("127.0.0.1",0));self.server.listen(1)
        self.port=self.server.getsockname()[1]
        self.thread=threading.Thread(target=self.serve,daemon=True)

    def dispatch(self, text):
        self.commands.append(text)
        if text == self.error_command:
            raise RuntimeError("injected Tcl error\nwith a second line")
        if text == "info commands read_memory":
            return "read_memory"
        if text == "reset halt":
            self.board.reset_halt();return ""
        if text == "wait_halt 5000":
            if self.board.running:
                raise RuntimeError("not halted")
            return ""
        if text == "halt":
            self.board.halt();return ""
        if text == "dict get [get_reg -force {pc}] pc":
            return hex(self.board.pc())
        fields=text.split()
        if fields[0] == "write_memory":
            values=[int(v.strip("{}"),0) for v in fields[3:]]
            self.board.write_words(int(fields[1],0),values);return ""
        if fields[0] == "read_memory":
            return " ".join(hex(v) for v in self.board.read_words(int(fields[1],0),int(fields[3])))
        if fields[0] == "resume":
            self.board.resume(int(fields[1],0));return ""
        raise RuntimeError("unexpected command: "+text)

    def serve(self):
        try:
            conn,_=self.server.accept()
            with conn:
                conn.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
                pending=bytearray()
                while True:
                    data=conn.recv(65536)
                    if not data:
                        break
                    pending.extend(data)
                    while b"\x1a" in pending:
                        end=pending.index(0x1a)
                        request=bytes(pending[:end]).decode();del pending[:end+1]
                        prefix="set __int22_rc [catch {"
                        suffix='} __int22_value]; format "%d\\n%s" $__int22_rc $__int22_value'
                        try:
                            if not request.startswith(prefix) or not request.endswith(suffix):
                                raise RuntimeError("bad Tcl catch/format envelope")
                            response="0\n"+self.dispatch(request[len(prefix):-len(suffix)])
                        except Exception as error:
                            response="1\n"+str(error)
                        frame=response.encode()+b"\x1a"
                        conn.sendall(frame[:1]);conn.sendall(frame[1:4]);conn.sendall(frame[4:])
        finally:
            self.server.close()

    def __enter__(self):
        self.thread.start();return self

    def __exit__(self, *unused):
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            raise RuntimeError("Offline Tcl server did not close")


class BatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=batch.catalog()
        cls.root=batch.workspace() / "tests" / datetime.datetime.now().strftime("firmware_batch_tests_%Y%m%d_%H%M%S_%f")
        cls.root.mkdir(parents=True)
        cls.pair=[c for c in cls.cases if c["name"] in ("raw_full_b4_cpu","raw_full_b4_raw")]

    def run_fixture(self, cases=None, fault=None, fail_fast=False):
        cases=cases or self.pair
        target=BoardFixture(cases,fault)
        args=batch.parser().parse_args(["--run"]+(["--fail-fast"] if fail_fast else []))
        out=self.root/self._testMethodName
        result=batch.run_batch(target,cases,args,out,lambda text:None)
        self.assertEqual(result,json.loads((out/"result.json").read_text()))
        return result,target,out

    def test_catalog_has_62_unique_complete_images(self):
        self.assertEqual(len(self.cases),62)
        self.assertEqual(len({c["name"] for c in self.cases}),62)
        self.assertFalse(any("selftest" in c["name"] or "partial" in c["name"] for c in self.cases))
        self.assertEqual([len(c["checks"]) for c in self.pair],[96,96])
        for case in self.cases:
            self.assertTrue((case["firmware_root"]/"image_manifest.json").is_file(),case["name"])
            word=struct.unpack_from("<I",case["binary"].read_bytes(),case["halt_pc"]-batch.BASE)[0]
            self.assertEqual(word,0x6f,case["name"])

    def test_full_catalog_control_flow(self):
        result,target,out=self.run_fixture(self.cases)
        self.assertEqual(result["status"],"PASS")
        self.assertEqual((result["passed"],target.resets,target.resumes),(62,62,62))
        self.assertEqual(len(result["speedups"]),12)
        self.assertTrue((out/"summary.md").is_file() and (out/"summary.csv").is_file())

    def test_user_measured_pair_ratio(self):
        result,_,_=self.run_fixture()
        self.assertAlmostEqual(result["speedups"][0]["speedup"],180232/12349)

    def test_report_replace_retries_temporary_permission_error(self):
        original = Path.replace
        attempts = []

        def replace(path, target):
            attempts.append(path)
            if len(attempts) <= 2:
                raise PermissionError("temporary file sharing violation")
            return original(path, target)

        with patch.object(Path, "replace", replace), patch.object(batch.time, "sleep") as sleep:
            result, _, _ = self.run_fixture()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(sleep.call_count, 2)

    def test_report_replace_failure_retains_last_result_and_temporary_file(self):
        out = self.root / self._testMethodName
        out.mkdir()
        (out / "result.json").write_bytes(b'{"previous":true}')
        report = dict(cases=[], selected=0, status="ERROR", environment="Offline file fixture")
        with patch.object(Path, "replace", side_effect=PermissionError("persistent denial")) as replace:
            with patch.object(batch.time, "sleep"), self.assertRaises(PermissionError):
                batch.save_report(out, report)
        self.assertEqual(replace.call_count, 4)
        self.assertEqual((out / "result.json").read_bytes(), b'{"previous":true}')
        self.assertEqual(json.loads((out / "result.json.tmp").read_text()), report)

    def test_original_first_two_samples_zero_is_detected(self):
        result,_,_=self.run_fixture(fault="first_two_samples_zero")
        self.assertEqual([r["status"] for r in result["cases"]],["FAIL","PASS"])
        self.assertEqual(len(result["cases"][0]["mismatches"]),16)
        self.assertEqual(result["speedups"],[])

    def test_wrong_tag_is_not_pass(self):
        result,_,_=self.run_fixture(fault="wrong_tag")
        self.assertEqual(result["passed"],0)
        self.assertEqual(result["speedups"],[])

    def test_incomplete_run_does_not_resume_for_polling(self):
        result,target,_=self.run_fixture(fault="incomplete")
        self.assertEqual(result["passed"],0)
        self.assertEqual(target.resumes,2)
        self.assertTrue(all(not c["timing_valid"] for c in result["cases"]))

    def test_partial_load_aborts_before_resume(self):
        result,target,_=self.run_fixture(fault="partial_load")
        self.assertEqual(result["status"],"ERROR")
        self.assertEqual(target.resumes,0)
        self.assertEqual(result["remaining"],1)

    def test_cpu_cannot_reuse_old_npu_counters(self):
        result,_,_=self.run_fixture(fault="cpu_uses_npu")
        self.assertEqual(result["cases"][0]["status"],"FAIL")

    def test_bad_overlap_union_is_detected(self):
        case=[c for c in self.pair if c["backend"] == "raw"]
        result,_,_=self.run_fixture(case,fault="bad_overlap")
        self.assertEqual(result["status"],"FAIL")

    def test_fail_fast_and_partial_summary(self):
        result,_,_=self.run_fixture(fault="first_two_samples_zero",fail_fast=True)
        self.assertEqual((result["failed"],result["remaining"]),(1,1))

    def test_interrupt_halts_and_keeps_evidence(self):
        result,target,_=self.run_fixture(fault="interrupt")
        self.assertEqual(result["status"],"INTERRUPTED")
        self.assertFalse(target.running)

    def test_selection_rejects_typo_before_connect(self):
        args=batch.parser().parse_args(["--list","--only","raw_typo_*"])
        with self.assertRaisesRegex(ValueError,"No selected image"):
            batch.select_cases(self.cases,args)

    def test_real_tcp_framing_and_bulk_load(self):
        board=BoardFixture(self.pair)
        with TclServer(board) as server:
            target=batch.OpenOcdTarget("127.0.0.1",server.port)
            target.environment="Local Tcl protocol fixture; not FPGA execution"
            args=batch.parser().parse_args(["--run","--run-seconds","0.001"])
            result=batch.run_batch(target,self.pair,args,self.root/self._testMethodName,lambda text:None)
        self.assertEqual(result["status"],"PASS",result.get("error"))
        writes=[s for s in server.commands if s.startswith("write_memory 0x800")]
        self.assertEqual(len(writes),128)
        self.assertEqual((board.resets,board.resumes),(2,2))
        self.assertIn("dict get [get_reg -force {pc}] pc",server.commands)

    def test_real_tcp_catches_multiline_tcl_error(self):
        board=BoardFixture(self.pair)
        with TclServer(board,error_command="reset halt") as server:
            target=batch.OpenOcdTarget("127.0.0.1",server.port)
            args=batch.parser().parse_args(["--run"])
            result=batch.run_batch(target,self.pair,args,self.root/self._testMethodName,lambda text:None)
        self.assertEqual(result["status"],"ERROR")
        self.assertIn("injected Tcl error\nwith a second line",result["error"])
        self.assertEqual(board.resumes,0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
