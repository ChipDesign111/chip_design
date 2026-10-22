"""Power-on derivation and cleanup regressions; Python 3.8+, no EDA/PDK.

Run: python -m unittest discover -s eda/pnr -p test_postroute_poweron.py -v
The real child processes below are Python fixtures, never simulators. Prepared
netlist/model/SDF fixtures do not establish post-route simulation acceptance.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


DRIVER = load("poweron_parallel", HERE/"run_postroute_parallel.py")
RUNNER = DRIVER.load_runner()
FIXTURE = load("poweron_input_fixtures", HERE/"test_postroute_inputs.py")
FROZEN_HELPER = "a66fea1baadda1089601a26ee698f493d7cdb4eeb44757b415f70d5da68703fe"


def source_hashes():
    paths = [HERE/"run_postroute_parallel.py", HERE/"run_postroute.py", RUNNER.TB,
             RUNNER.FIRMWARE, ROOT/"rtl/manifest.json", HERE/"test_postroute_parallel.py"]
    paths += sorted(path for path in (ROOT/"rtl").rglob("*") if path.is_file())
    firmware = json.loads(RUNNER.FIRMWARE.read_text())
    paths += [RUNNER.FIRMWARE.parent/item["image"] for item in firmware["cases"].values()]
    return {str(path): RUNNER.sha(path) for path in sorted(set(paths))}


class PostroutePoweronTests(unittest.TestCase):
    def setUp(self):
        self.assertEqual(RUNNER.sha(HERE/"run_postroute_parallel.py"), FROZEN_HELPER)
        self.assertEqual(RUNNER.sha(HERE/"run_postroute.py"), DRIVER.FROZEN_RUNNER_SHA256)
        self.assertEqual(RUNNER.sha(RUNNER.TB), RUNNER.FROZEN_TB_SHA256)
        self.frozen_sources = source_hashes()
        scratch = ROOT/"eda/work/postroute-poweron-selftest"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="case-", dir=str(scratch))
        self.base = Path(self.temporary.name).resolve()
        self.assertEqual(self.base.parent, scratch.resolve())

    def tearDown(self):
        try:
            self.assertEqual(source_hashes(), self.frozen_sources)
        finally:
            self.temporary.cleanup()

    def prepare(self, directory, settle_ns=0, extra=()):
        directory.mkdir(parents=True, exist_ok=True)
        net, sdf, model = (directory/name for name in ("fixture.v", "fixture.sdf", "cells.v"))
        net.write_text(FIXTURE.NETLIST)
        sdf.write_text(FIXTURE.SDF)
        model.write_text(FIXTURE.MODELS)
        out = directory/"prepared"
        argv = ["--out", str(out), "--netlist", str(net), "--sdf", str(sdf),
                "--stdcell-model", str(model), "--sram-model", str(model), "--io-model", str(model),
                "--design-top", "chip", "--xrun-arg=-caint"] + list(extra)
        with contextlib.redirect_stdout(io.StringIO()):
            result = DRIVER.prepare(RUNNER, argv, out, settle_ns)
        return out, result

    def test_poweron_changes_exactly_one_byte_region_and_one_argv_per_case(self):
        out, result = self.prepare(self.base/"derive", 1000)
        info = result["poweron_settle"]
        before = Path(info["prepared_base_testbench"]).read_bytes()
        after = Path(info["derived_testbench"]).read_bytes()
        ending = b"\r\n" if b"\r\n" in before else b"\n"
        old = b"    always #(CLK_PERIOD_NS/2.0) clk_i = ~clk_i;" + ending
        new = ending.join((b"    initial begin", b"        #1000.0;",
                           b"        forever #(CLK_PERIOD_NS/2.0) clk_i = ~clk_i;", b"    end", b""))
        self.assertEqual(before.count(old), 1)
        self.assertEqual(after, before.replace(old, new, 1))
        self.assertEqual(info["derived_sha256"], RUNNER.sha(Path(info["derived_testbench"])))
        self.assertEqual(info["original_frozen_testbench_sha256"], RUNNER.FROZEN_TB_SHA256)
        self.assertEqual(info["changed_regions"], 1)
        self.assertEqual((info["first_system_posedge_ns"], info["reset_release_after_eighth_negedge_ns"]), (1010, 1160))
        snapshot = json.loads((out/"original_preparation.json").read_text())
        self.assertEqual(snapshot["status"], "PREPARED")
        self.assertNotIn("poweron_settle", snapshot)
        self.assertEqual([item["name"] for item in result["checks"]], ["synthetic", "dma"])
        for item in info["command_changes"]:
            original, actual = item["original_command"], item["actual_command"]
            self.assertEqual(len(original), len(actual))
            self.assertEqual([i for i, pair in enumerate(zip(original, actual)) if pair[0] != pair[1]],
                             [item["changed_argument_index"]])
            self.assertEqual(json.loads((out/item["name"]/"command_original.json").read_text()), original)
            self.assertEqual(json.loads((out/item["name"]/"command.json").read_text()), actual)
            for flag in ("-caint", "+define+NTC+RECREM", "-negdelay", "-sdf_cmd_file"):
                self.assertIn(flag, actual)
            self.assertIsNone(RUNNER.BAD_TIMING_OPTIONS.search(" ".join(actual)))
            for parameter in ("CLK_PERIOD_NS=20.0", "TCK_PERIOD_NS=100.0", "BOOTS=2"):
                self.assertIn("tb_soc_pins."+parameter, actual)
        self.assertFalse(result["functional_timing_checks_disabled"])
        self.assertEqual(result["status"], "PREPARED")
        self.assertEqual(result["sdf_compile"]["status"], "PREPARED")
        self.assertFalse((out/"annotate.sdf.X").exists())

    def test_zero_is_default_and_preserves_original_prepared_commands(self):
        args, forwarded = DRIVER.arguments(["--out", str(self.base/"unused"), "--poweron-settle-ns=0"])
        self.assertEqual(args.poweron_settle_ns, 0)
        self.assertEqual(forwarded, ["--out", str(self.base/"unused")])
        args, _ = DRIVER.arguments(["--out", str(self.base/"unused")])
        self.assertEqual(args.poweron_settle_ns, 0)
        out, result = self.prepare(self.base/"zero")
        self.assertNotIn("poweron_settle", result)
        self.assertFalse((out/"tb_soc_pins_poweron_settle.sv").exists())
        self.assertFalse((out/"original_preparation.json").exists())
        for record in result["checks"]:
            self.assertEqual(record["status"], "PREPARED")
            self.assertEqual(json.loads((out/record["name"]/"command.json").read_text()), record["command"])

    def test_illegal_settle_and_missing_or_duplicate_clock_generator_are_rejected(self):
        for value in ("-1", "1", "500", "1001", "1000.0"):
            with self.subTest(settle=value), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                DRIVER.arguments(["--out", str(self.base/"unused"), "--poweron-settle-ns="+value])
        for mode in ("changed", "duplicated"):
            out, result = self.prepare(self.base/mode)
            source = out/"tb_soc_pins_postroute.sv"
            before = source.read_bytes()
            old = b"    always #(CLK_PERIOD_NS/2.0) clk_i = ~clk_i;"
            ending = b"\r\n" if b"\r\n" in before else b"\n"
            altered = before.replace(old, old.replace(b"2.0", b"4.0"), 1) if mode == "changed" else before+old+ending
            source.write_bytes(altered)
            # Exercise anchor rejection independently of the prepared-hash guard.
            result["prepared_sha256"][source.relative_to(out).as_posix()] = RUNNER.sha(source)
            with self.assertRaisesRegex(ValueError, "exactly one frozen system-clock generator"):
                DRIVER.derive_poweron_testbench(RUNNER, out, result, 1000)
            self.assertFalse((out/"tb_soc_pins_poweron_settle.sv").exists())

    def test_timing_suppression_is_still_rejected_before_derivation(self):
        for index, flag in enumerate(("-notimingchecks", "-nospecify", "-sdf_no_timing")):
            with self.subTest(flag=flag), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.prepare(self.base/("suppressed-"+str(index)), 1000, ["--xrun-arg="+flag])

    def exercise_cleanup(self, timeout_failure):
        out = self.base
        cases = []
        start_workers = out/"workers_go"
        ready_files = []
        for name in DRIVER.REQUIRED_CASES:
            folder = out/name
            folder.mkdir()
            ready = folder/"ready"
            ready_files.append(ready)
            # Both real children must be running before either failure is
            # released. Python startup speed is not the behavior under test.
            action = "time.sleep(30)" if timeout_failure or name == "dma" else "raise SystemExit(7)"
            code = ("from pathlib import Path\nimport time\n"
                    "Path('ready').write_text('ready')\n"
                    "while not Path('../workers_go').exists(): time.sleep(.01)\n" + action)
            command = [sys.executable, "-c", code]
            RUNNER.save(folder/"command.json", command)
            (folder/"sdf_annotation.cmd").write_text("Python fixture, not EDA")
            cases.append({"name": name, "status": "PREPARED", "command": command,
                          "sdf_command_raw": (folder/"sdf_annotation.cmd").read_text(),
                          "sdf_command_sha256": RUNNER.sha(folder/"sdf_annotation.cmd")})
        result = {"checks": cases, "input_sha256": {str(DRIVER.RUNNER_PATH): DRIVER.FROZEN_RUNNER_SHA256},
                  "prepared_sha256": {}, "structural_audit": {"status": "PASS"},
                  "sdf_compile": {"status": "PREPARED", "command": [sys.executable, "-c",
                                  "from pathlib import Path; Path('annotate.sdf.X').write_bytes(b'Python fixture')"]}}
        original_popen, original_stop = subprocess.Popen, DRIVER.stop_process
        processes, cleanup_pids, workers = [], [], []
        timeout = 15
        fixture_clock = [0.0]

        def capture(*args, **kwargs):
            process = original_popen(*args, **kwargs)
            if args[0][0] == sys.executable:
                processes.append(process)
            if kwargs.get("cwd") and Path(kwargs["cwd"]) in [out/name for name in DRIVER.REQUIRED_CASES]:
                workers.append(process)
                if len(workers) == 2:
                    deadline = time.monotonic()+timeout
                    while not all(path.is_file() for path in ready_files):
                        self.assertTrue(all(child.poll() is None for child in workers),
                                        "A fixture child exited before the readiness barrier")
                        if time.monotonic() >= deadline:
                            self.fail("Both fixture children must reach the readiness barrier")
                        time.sleep(.01)
                    start_workers.write_text("go")
                    # Only the driver's deadline clock advances, after both
                    # children have reached the barrier. The real compiler
                    # still gets a generous subprocess.wait timeout.
                    if timeout_failure:
                        fixture_clock[0] = timeout+1.0
            return process

        def signal_during_first_cleanup(process):
            cleanup_pids.append(process.pid)
            if len(cleanup_pids) == 1:
                self.assertGreater(DRIVER._DEFER_TERMINATION, 0)
                # First signal after rc7/timeout already entered stop_process.
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            original_stop(process)

        try:
            with DRIVER.termination_handlers(), contextlib.redirect_stderr(io.StringIO()):
                with contextlib.ExitStack() as stack:
                    stack.enter_context(mock.patch.object(DRIVER.subprocess, "Popen", side_effect=capture))
                    stack.enter_context(mock.patch.object(DRIVER, "stop_process", side_effect=signal_during_first_cleanup))
                    if timeout_failure:
                        stack.enter_context(mock.patch.object(DRIVER, "time", SimpleNamespace(
                            monotonic=lambda: fixture_clock[0], sleep=time.sleep)))
                    code = DRIVER.execute(RUNNER, out, result, 2, timeout)
            self.assertEqual(code, 128+signal.SIGTERM)
            self.assertEqual(result["sdf_compile"]["status"], "PASS")
            self.assertEqual(len(workers), 2)
            self.assertTrue(all(path.is_file() for path in ready_files))
            self.assertTrue(start_workers.is_file())
            self.assertEqual(len(cleanup_pids), 2)
            self.assertEqual(set(cleanup_pids), {process.pid for process in workers})
            self.assertTrue(all(process.poll() is not None for process in processes))
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual([case["status"] for case in cases], ["FAIL", "ABORTED"])
            self.assertTrue(all(case["exit_code"] is not None for case in cases))
            self.assertTrue(all("elapsed_seconds" in case for case in cases))
            if timeout_failure:
                self.assertEqual(cases[0]["error"], "Per-case timeout after 15 seconds")
            else:
                self.assertEqual(cases[0]["exit_code"], 7)
            self.assertEqual(json.loads((out/"audit.json").read_text())["status"], "FAIL")
        finally:
            for process in processes:
                if process.poll() is None:
                    original_stop(process)

    def test_first_sigterm_during_nonzero_failure_cleanup_reaps_all_workers(self):
        self.exercise_cleanup(False)

    def test_first_sigterm_during_timeout_cleanup_reaps_all_workers(self):
        self.exercise_cleanup(True)


if __name__ == "__main__":
    unittest.main()
