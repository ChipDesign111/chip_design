"""Local process/contract regressions; no EDA executable or PDK is invoked."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


DRIVER = module("postroute_parallel", HERE / "run_postroute_parallel.py")
RUNNER = DRIVER.load_runner()
FIXTURE = module("postroute_input_fixtures", HERE / "test_postroute_inputs.py")


class LocalRunner:
    now = staticmethod(RUNNER.now)

    @staticmethod
    def audit_case(out, record):
        return {"status": "PASS" if record["exit_code"] == 0 and
                (out / record["name"] / "console.log").read_text().strip() == "FIXTURE_PASS" else "FAIL"}


class ParallelTests(unittest.TestCase):
    def setUp(self):
        scratch = HERE.parent / "work/postroute-parallel-selftest"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="process-", dir=str(scratch))
        self.base = Path(self.temporary.name).resolve()
        self.assertEqual(self.base.parent, scratch.resolve())

    def tearDown(self):
        self.temporary.cleanup()

    def records(self, codes):
        checks = []
        for name, code in zip(DRIVER.REQUIRED_CASES, codes):
            (self.base / name).mkdir()
            checks.append({"name": name, "status": "PREPARED", "command": [sys.executable, "-c", code]})
        return {"checks": checks}

    def run_workers(self, result, timeout=10):
        processes = []
        original = subprocess.Popen

        def capture(*args, **kwargs):
            process = original(*args, **kwargs)
            if args[0][0] == sys.executable and args[0][1] == "-c":
                processes.append((process, args[0], kwargs["cwd"]))
            return process

        with mock.patch.object(DRIVER.subprocess, "Popen", side_effect=capture):
            try:
                DRIVER.run_cases(LocalRunner(), self.base, result, 2, timeout, lambda: None, lambda: None)
            finally:
                self.assertTrue(all(process.poll() is not None for process, _, _ in processes),
                                "Every launched worker must have been reaped")
        return processes

    def test_real_children_overlap_and_receive_exact_prepared_argv_and_cwd(self):
        code = ("from pathlib import Path; import json,sys,time; p=Path.cwd(); "
                "(p.parent/(p.name+'.ready')).write_text('ready'); "
                "(p/'argv.json').write_text(json.dumps(sys.argv[1:])); "
                "deadline=time.monotonic()+5\n"
                "while len(list(p.parent.glob('*.ready')))<2 and time.monotonic()<deadline: time.sleep(.02)\n"
                "assert len(list(p.parent.glob('*.ready')))==2; print('FIXTURE_PASS')")
        result = self.records([code, code])
        for record in result["checks"]:
            record["command"] += ["-caint", "+define+NTC+RECREM", "-negdelay", "-defparam", 'tb.INIT_FILE="a b.hex"']
        originals = json.loads(json.dumps(result["checks"]))
        processes = self.run_workers(result)
        self.assertEqual([r["status"] for r in result["checks"]], ["PASS", "PASS"])
        for record, original, (_, command, cwd) in zip(result["checks"], originals, processes):
            self.assertEqual(command, original["command"])
            self.assertEqual(cwd, str(self.base / record["name"]))
            self.assertEqual(json.loads((Path(cwd)/"argv.json").read_text()), command[3:])

    def test_nonzero_worker_aborts_and_reaps_other_worker(self):
        fail = ("from pathlib import Path; import sys,time; p=Path.cwd().parent; "
                "deadline=time.monotonic()+5\n"
                "while not (p/'sibling.ready').exists() and time.monotonic()<deadline: time.sleep(.02)\n"
                "sys.exit(7)")
        slow = "from pathlib import Path; import time; (Path.cwd().parent/'sibling.ready').write_text('ready'); time.sleep(30)"
        result = self.records([fail, slow])
        with self.assertRaisesRegex(RuntimeError, "synthetic"):
            self.run_workers(result)
        self.assertEqual(result["checks"][0]["status"], "FAIL")
        self.assertEqual(result["checks"][0]["exit_code"], 7)
        self.assertEqual(result["checks"][1]["status"], "ABORTED")
        self.assertIsInstance(result["checks"][1]["exit_code"], int)

    def test_timeout_aborts_sibling_instead_of_reporting_prepared_or_pass(self):
        result = self.records(["import time; time.sleep(30)"]*2)
        with self.assertRaises(TimeoutError):
            self.run_workers(result, timeout=.15)
        self.assertEqual([r["status"] for r in result["checks"]], ["FAIL", "ABORTED"])
        self.assertTrue(all(r["elapsed_seconds"] > 0 for r in result["checks"]))

    def test_cleanup_error_does_not_skip_remaining_worker(self):
        result = self.records(["import sys,time; time.sleep(.1); sys.exit(7)", "import time; time.sleep(30)"])
        stop = DRIVER.stop_process
        calls = []

        def stop_then_error(process):
            stop(process)
            calls.append(process.pid)
            if len(calls) == 1:
                raise RuntimeError("injected cleanup reporting error")

        with mock.patch.object(DRIVER, "stop_process", side_effect=stop_then_error):
            with self.assertRaisesRegex(RuntimeError, "synthetic"):
                self.run_workers(result)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(result["cleanup_errors"]), 1)
        self.assertEqual(result["checks"][1]["status"], "ABORTED")

    def test_signal_in_popen_registration_window_is_deferred_and_child_reaped(self):
        result = self.records(["import time; time.sleep(30)"]*2)
        original = subprocess.Popen
        processes = []

        def signal_after_spawn(*args, **kwargs):
            process = original(*args, **kwargs)
            if args[0][0] == sys.executable:
                processes.append(process)
                # Deterministically hit the gap after OS spawn but before the
                # assignment/active registration in the scheduling code.
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            return process

        with DRIVER.termination_handlers():
            with mock.patch.object(DRIVER.subprocess, "Popen", side_effect=signal_after_spawn):
                with self.assertRaises(DRIVER.TerminationRequested):
                    DRIVER.run_cases(LocalRunner(), self.base, result, 2, 10, lambda: None, lambda: None)
        self.assertTrue(all(process.poll() is not None for process in processes))
        self.assertEqual(len(processes), 1)
        self.assertEqual([r["status"] for r in result["checks"]], ["ABORTED", "ABORTED"])

    @unittest.skipUnless(os.name == "posix", "Unix service SIGTERM/process-group semantics")
    def test_sigterm_records_failure_and_reaps_worker_descendants(self):
        worker = ("from pathlib import Path; import subprocess,sys,time; "
                  "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
                  "Path('descendant.pid').write_text(str(child.pid)); time.sleep(30)")
        result = self.records([worker, worker])
        for record in result["checks"]:
            folder = self.base/record["name"]
            RUNNER.save(folder/"command.json", record["command"])
            (folder/"sdf_annotation.cmd").write_text("fixture command")
        result.update(input_sha256={str(DRIVER.RUNNER_PATH): DRIVER.FROZEN_RUNNER_SHA256}, prepared_sha256={},
                      structural_audit={"status": "PASS"}, sdf_compile={"status": "PREPARED", "command": [
                          sys.executable, "-c", "from pathlib import Path; Path('annotate.sdf.X').write_bytes(b'fixture')"]})
        fixture = self.base/"fixture.json"
        RUNNER.save(fixture, result)
        harness = self.base/"signal_harness.py"
        harness.write_text("import importlib.util,json,sys\nfrom pathlib import Path\n"
                           "spec=importlib.util.spec_from_file_location('driver'," + repr(str(Path(DRIVER.__file__))) + ")\n"
                           "d=importlib.util.module_from_spec(spec); spec.loader.exec_module(d)\n"
                           "out=Path(" + repr(str(self.base)) + ")\n"
                           "r=json.loads((out/'fixture.json').read_text())\n"
                           "with d.termination_handlers(): code=d.execute(d.load_runner(),out,r,2,20)\n"
                           "sys.exit(code)\n")
        process = subprocess.Popen([sys.executable, str(harness)], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
        try:
            deadline = time.monotonic()+10
            files = [self.base/name/"descendant.pid" for name in DRIVER.REQUIRED_CASES]
            while not all(path.is_file() for path in files) and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue(all(path.is_file() for path in files))
            descendants = [int(path.read_text()) for path in files]
            os.kill(process.pid, signal.SIGTERM)
            self.assertEqual(process.wait(timeout=15), 128+signal.SIGTERM)
            actual = json.loads((self.base/"results.json").read_text())
            self.assertEqual(actual["status"], "FAIL")
            self.assertEqual([r["status"] for r in actual["checks"]], ["ABORTED", "ABORTED"])
            for pid in descendants:
                deadline = time.monotonic()+5
                while time.monotonic() < deadline:
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        break
                    procstat = Path("/proc")/str(pid)/"stat"
                    if procstat.is_file() and procstat.read_text().split(") ", 1)[1].startswith("Z"):
                        break  # Dead child awaiting init/subreaper collection.
                    time.sleep(.05)
                else:
                    self.fail("A live worker descendant survived SIGTERM cleanup: " + str(pid))
        finally:
            if process.poll() is None:
                os.kill(process.pid, signal.SIGTERM)
                process.wait(timeout=15)

    def test_failed_real_compile_records_rc_and_hash_and_aborts_unlaunched_cases(self):
        result = self.records(["raise AssertionError('must not run')"]*2)
        (self.base/"annotate.sdf").write_text("fixture SDF, not an EDA test")
        for record in result["checks"]:
            folder = self.base / record["name"]
            RUNNER.save(folder/"command.json", record["command"])
            (folder/"sdf_annotation.cmd").write_text("fixture command")
        result.update(input_sha256={str(DRIVER.RUNNER_PATH): DRIVER.FROZEN_RUNNER_SHA256},
                      prepared_sha256={"annotate.sdf": RUNNER.sha(self.base/"annotate.sdf")},
                      structural_audit={"status": "PASS"},
                      sdf_compile={"status": "PREPARED", "command": [sys.executable, "-c",
                                   "from pathlib import Path; import sys; Path('annotate.sdf.X').write_bytes(b'partial fixture'); sys.exit(9)"]})
        self.assertEqual(DRIVER.execute(RUNNER, self.base, result, 2, 10), 1)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["sdf_compile"]["exit_code"], 9)
        self.assertEqual(result["sdf_compile"]["compiled_sha256"], RUNNER.sha(self.base/"annotate.sdf.X"))
        self.assertEqual([r["status"] for r in result["checks"]], ["ABORTED", "ABORTED"])
        self.assertEqual(json.loads((self.base/"audit.json").read_text())["status"], "FAIL")
        self.assertIn(str(Path(DRIVER.__file__).resolve()), result["input_sha256"])

    def test_original_dry_preparation_has_full_unexecuted_matrix_and_no_compiled_sdf(self):
        net, sdf, model = (self.base/name for name in ("fixture.v", "fixture.sdf", "cells.v"))
        net.write_text(FIXTURE.NETLIST)
        sdf.write_text(FIXTURE.SDF)
        model.write_text(FIXTURE.MODELS)
        out = self.base/"prepared"
        args = ["--parallel", "2", "--netlist", str(net), "--sdf", str(sdf), "--out", str(out),
                "--stdcell-model", str(model), "--sram-model", str(model), "--io-model", str(model),
                "--design-top", "chip", "--xrun-arg=-caint", "--sdf-corner", "MINIMUM"]
        parsed, forwarded = DRIVER.arguments(args)
        self.assertNotIn("--parallel", forwarded)
        self.assertEqual(forwarded, args[2:])
        with contextlib.redirect_stdout(io.StringIO()):
            result = DRIVER.prepare(RUNNER, forwarded, out)
        self.assertEqual(result["status"], "PREPARED")
        self.assertEqual(result["sdf_compile"]["status"], "PREPARED")
        self.assertFalse((out/"annotate.sdf.X").exists())
        self.assertEqual([r["name"] for r in result["checks"]], ["synthetic", "dma"])
        for record in result["checks"]:
            self.assertEqual(record["status"], "PREPARED")
            self.assertEqual(json.loads((out/record["name"]/"command.json").read_text()), record["command"])
            for option in ("-caint", "+define+NTC+RECREM", "-negdelay", "-sdf_cmd_file"):
                self.assertIn(option, record["command"])
            self.assertIn('MTM_CONTROL = "MINIMUM";', record["sdf_command_raw"])
        self.assertEqual(RUNNER.sha(DRIVER.RUNNER_PATH), DRIVER.FROZEN_RUNNER_SHA256)

    def test_partial_or_nonexecuting_modes_and_excess_parallelism_are_rejected(self):
        for option in ("--only=synthetic", "--on=synthetic", "--dry-run", "--dry", "--audit-only", "--audit"):
            with self.subTest(option=option), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                DRIVER.arguments(["--out", str(self.base/"unused"), option])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            DRIVER.arguments(["--out", str(self.base/"unused"), "--parallel=3"])


if __name__ == "__main__":
    unittest.main()
