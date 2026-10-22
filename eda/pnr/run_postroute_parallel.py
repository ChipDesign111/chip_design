#!/usr/bin/env python3
"""Schedule the frozen post-route runner's synthetic+dma commands concurrently.

Use the same arguments as run_postroute.py, with an explicit fresh --out.
--parallel 2 (default) runs at most two case processes in this invocation;
--parallel 1 is useful for comparison. Each SDF corner needs a separate output.
The original runner prepares every command with --dry-run; this driver then
really compiles the SDF and executes/audits both cases. Preparation is not PASS.
This does not run multiple SDF corners or change any simulator/test parameters.
"""
import argparse
import copy
from contextlib import contextmanager
import difflib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
RUNNER_PATH = HERE / "run_postroute.py"
FROZEN_RUNNER_SHA256 = "b43edb24af41fbcf3fa21049e0938e4c16382519a1546e5d18174754ed00b30b"
REQUIRED_CASES = ("synthetic", "dma")
_DEFER_TERMINATION = 0
_PENDING_TERMINATION = None


class TerminationRequested(BaseException):
    def __init__(self, number):
        self.number = number
        super().__init__("Driver received signal " + str(number))


@contextmanager
def termination_handlers():
    """Turn service/shell termination into the same fail-and-reap path."""
    numbers = [getattr(signal, name) for name in ("SIGINT", "SIGTERM", "SIGHUP") if hasattr(signal, name)]
    previous = {number: signal.getsignal(number) for number in numbers}

    def handle(number, _frame):
        global _PENDING_TERMINATION
        # A repeated termination request must not interrupt sibling cleanup.
        for item in numbers:
            signal.signal(item, signal.SIG_IGN)
        if _DEFER_TERMINATION:
            _PENDING_TERMINATION = number
            return
        raise TerminationRequested(number)

    try:
        for number in numbers:
            signal.signal(number, handle)
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


@contextmanager
def deferred_termination():
    """Register a newly spawned child before acting on a termination signal."""
    global _DEFER_TERMINATION, _PENDING_TERMINATION
    _DEFER_TERMINATION += 1
    try:
        yield
    finally:
        _DEFER_TERMINATION -= 1
        if not _DEFER_TERMINATION and _PENDING_TERMINATION is not None:
            number, _PENDING_TERMINATION = _PENDING_TERMINATION, None
            raise TerminationRequested(number)


def load_runner():
    spec = importlib.util.spec_from_file_location("frozen_postroute_runner", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.sha(RUNNER_PATH) != FROZEN_RUNNER_SHA256:
        raise ValueError("run_postroute.py is not the reviewed frozen b43 runner")
    return module


def arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--parallel", type=int, choices=(1, 2), default=2)
    parser.add_argument("--poweron-settle-ns", type=int, choices=(0, 1000), default=0,
                        help="Explicit derived TB: wait 1000 ns before the original clock loop; 0 preserves original")
    parser.add_argument("--out", type=Path, required=True, help="Fresh directory under eda/work/")
    parser.add_argument("--timeout", type=int, default=10800, help="Original per-process timeout, forwarded unchanged")
    args, _ = parser.parse_known_args(argv)
    forwarded, index = [], 0
    while index < len(argv):
        token = argv[index]
        option = token.split("=", 1)[0]
        if option.startswith("--") and any(forbidden.startswith(option) for forbidden in
                                          ("--only", "--dry-run", "--audit-only")):
            parser.error("This driver requires the complete, actually executed synthetic+dma matrix: " + token)
        if option.startswith("--") and any(canonical.startswith(option) and option != canonical
                                          for canonical in ("--timeout", "--out")):
            parser.error("Use the full --timeout and --out option names: " + token)
        if option in ("--parallel", "--poweron-settle-ns"):
            index += 1 if "=" in token else 2
        else:
            forwarded.append(token)
            index += 1
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args, forwarded


def prepare(runner, forwarded, out, poweron_settle_ns=0):
    """Call the original main, adding only its preparation flag."""
    previous = sys.argv
    try:
        sys.argv = [str(RUNNER_PATH)] + list(forwarded) + ["--dry-run"]
        code = runner.main()
    finally:
        sys.argv = previous
    if code != 0:
        raise RuntimeError("Frozen runner preparation failed: " + str(code))
    result = json.loads((out / "results.json").read_text())
    records = result.get("checks", [])
    if (result.get("status") != "PREPARED" or tuple(item.get("name") for item in records) != REQUIRED_CASES
            or any(item.get("status") != "PREPARED" for item in records)
            or result.get("sdf_compile", {}).get("status") != "PREPARED"):
        raise ValueError("Original preparation did not produce the complete PREPARED matrix")
    if (out / "annotate.sdf.X").exists():
        raise ValueError("Preparation unexpectedly produced compiled SDF")
    if poweron_settle_ns:
        derive_poweron_testbench(runner, out, result, poweron_settle_ns)
    return result


def derive_poweron_testbench(runner, out, result, settle_ns):
    """Change exactly the clock-generator region of the prepared TB copy.

    The original frozen TB, original runner, RTL, firmware and all timing/model
    switches are retained. Actual command arrays intentionally change one source
    argument; the original arrays, single-region diff and both hashes persist.
    """
    if settle_ns != 1000:
        raise ValueError("Only the explicitly reviewed 1000 ns power-on settle is supported")
    if runner.sha(runner.TB) != runner.FROZEN_TB_SHA256:
        raise ValueError("Frozen original pin TB changed")
    binding = result["testbench_binding"]["kind"]
    if binding == "frozen_testbench_direct":
        source = runner.TB
    elif binding == "top_port_supply_wrapper":
        source = out/"tb_soc_pins_postroute.sv"
        if runner.sha(source) != result["prepared_sha256"].get(source.relative_to(out).as_posix()):
            raise ValueError("Prepared supply-wrapper TB changed")
    else:
        raise ValueError("Unknown prepared TB binding: " + str(binding))
    before = source.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in before else "\n"
    old = "    always #(CLK_PERIOD_NS/2.0) clk_i = ~clk_i;" + newline
    new = newline.join(("    initial begin", "        #1000.0;",
                        "        forever #(CLK_PERIOD_NS/2.0) clk_i = ~clk_i;", "    end", ""))
    if before.count(old) != 1:
        raise ValueError("Expected exactly one frozen system-clock generator")
    original_preparation = out/"original_preparation.json"
    runner.save(original_preparation, copy.deepcopy(result))
    derived, patch = out/"tb_soc_pins_poweron_settle.sv", out/"poweron_testbench.diff"
    after = before.replace(old, new, 1)
    derived.write_bytes(after.encode("utf-8"))
    patch.write_bytes("".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                               fromfile=str(source), tofile=str(derived))).encode("utf-8"))
    changes = []
    for record in result["checks"]:
        original = list(record["command"])
        if original.count(str(source)) != 1:
            raise ValueError("Exactly one original TB command argument required: " + record["name"])
        index = original.index(str(source))
        actual = list(original)
        actual[index] = str(derived)
        original_file = out/record["name"]/"command_original.json"
        runner.save(original_file, original)
        runner.save(out/record["name"]/"command.json", actual)
        record["command"] = actual
        changes.append({"name": record["name"], "changed_argument_index": index,
                        "original_command": original, "actual_command": actual,
                        "original_testbench_argument": str(source), "actual_testbench_argument": str(derived)})
        result["prepared_sha256"][original_file.relative_to(out).as_posix()] = runner.sha(original_file)
    for path in (derived, patch, original_preparation):
        result["prepared_sha256"][path.relative_to(out).as_posix()] = runner.sha(path)
    result["poweron_settle"] = {"enabled": True, "settle_ns": settle_ns, "changed_regions": 1,
                               "original_frozen_testbench": str(runner.TB),
                               "original_frozen_testbench_sha256": runner.sha(runner.TB),
                               "prepared_base_testbench": str(source), "prepared_base_sha256": runner.sha(source),
                               "derived_testbench": str(derived), "derived_sha256": runner.sha(derived),
                               "diff": patch.name, "diff_sha256": runner.sha(patch), "command_changes": changes,
                               "first_system_posedge_ns": 1010, "reset_release_after_eighth_negedge_ns": 1160,
                               "sys_period_ns": 20, "tck_period_ns": 100,
                               "scope": "External system clock held low during 1000 ns power-on settling; original relative reset/JTAG sequencing and all timing checks remain"}
    runner.save(out/"results.json", result)


def assert_unchanged(runner, out, result, contract):
    for name, expected in result["input_sha256"].items():
        path = Path(name)
        if not path.is_file() or runner.sha(path) != expected:
            raise ValueError("Frozen input changed/unavailable: " + name)
    for name, expected in result["prepared_sha256"].items():
        path = out / name
        if not path.is_file() or runner.sha(path) != expected:
            raise ValueError("Prepared input changed: " + name)
    if result["sdf_compile"]["command"] != contract["sdf_compile_command"]:
        raise ValueError("Original SDF compiler command changed")
    if tuple(item["name"] for item in result["checks"]) != REQUIRED_CASES:
        raise ValueError("Original case matrix changed")
    for record in result["checks"]:
        name = record["name"]
        original = contract["cases"][name]
        if record["command"] != original["command"]:
            raise ValueError("Original simulator command changed: " + name)
        for filename, expected in original["file_sha256"].items():
            if runner.sha(out / name / filename) != expected:
                raise ValueError("Original case command input changed: " + name + "/" + filename)


def process_options():
    if os.name == "posix":
        return {"start_new_session": True}
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    raise RuntimeError("Process-tree cleanup is supported only on POSIX and Windows")


def stop_process(process):
    """Reap the process and its own process group/tree on failure."""
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        # The leader may have exited while a simulator child still runs.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif os.name == "nt" and process.poll() is None:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if process.poll() is None:
            process.kill()
    process.wait(timeout=10)


def run_compile(runner, out, result, timeout, persist):
    info = result["sdf_compile"]
    start = time.monotonic()
    info.update(status="RUNNING", started_utc=runner.now(), cwd=str(out))
    persist()
    process = None
    try:
        with (out / "sdf_compile.log").open("wb") as log:
            with deferred_termination():
                process = subprocess.Popen(info["command"], cwd=str(out), stdout=log,
                                           stderr=subprocess.STDOUT, **process_options())
                info["pid"] = process.pid
            persist()
            code = process.wait(timeout=timeout)
        info.update(exit_code=code, status="PASS" if code == 0 else "FAIL")
        compiled = out / "annotate.sdf.X"
        if compiled.is_file():
            info["compiled_sha256"] = runner.sha(compiled)
        else:
            info.update(status="FAIL", error="SDF compiler produced no annotate.sdf.X")
        if any(runner.diagnostics(runner.read(out / "sdf_compile.log"))):
            info.update(status="FAIL", error="Raw SDF compiler diagnostics found")
        if info["status"] != "PASS":
            raise RuntimeError(info.get("error", "SDF compiler failed: " + str(code)))
    except BaseException as exc:
        # Finish all recovery before acting on a newly arriving signal.
        with deferred_termination():
            if process is not None:
                try:
                    stop_process(process)
                except Exception as cleanup_error:
                    info["cleanup_error"] = str(cleanup_error)
                info["exit_code"] = process.poll()
            else:
                info["exit_code"] = None
            info.update(status="FAIL", error=str(exc) or type(exc).__name__)
            raise
    finally:
        compiled = out / "annotate.sdf.X"
        if compiled.is_file():
            info["compiled_sha256"] = runner.sha(compiled)
        info.update(finished_utc=runner.now(), elapsed_seconds=round(time.monotonic() - start, 3))
        persist()


def run_cases(runner, out, result, parallel, timeout, persist, invariant):
    """Execute original commands verbatim; a failed worker aborts its siblings."""
    pending, active = list(result["checks"]), []
    try:
        while pending or active:
            while pending and len(active) < parallel:
                record = pending.pop(0)
                invariant()
                folder = out / record["name"]
                log = (folder / "console.log").open("wb")
                start = time.monotonic()
                registered = False
                try:
                    with deferred_termination():
                        process = subprocess.Popen(record["command"], cwd=str(folder), stdout=log,
                                                   stderr=subprocess.STDOUT, **process_options())
                        active.append((record, process, log, start))
                        registered = True
                        record.update(status="RUNNING", pid=process.pid, cwd=str(folder), started_utc=runner.now())
                except BaseException as exc:
                    if not registered:
                        log.close()
                        record.update(status="FAIL", exit_code=None, elapsed_seconds=round(time.monotonic()-start, 3),
                                      error=str(exc) or type(exc).__name__, finished_utc=runner.now())
                    raise
                persist()
            for item in list(active):
                record, process, log, start = item
                code = process.poll()
                if code is None:
                    if time.monotonic() - start > timeout:
                        record.update(status="FAIL", error="Per-case timeout after " + str(timeout) + " seconds")
                        raise TimeoutError(record["name"] + " timed out")
                    continue
                log.close()
                record.update(status="PASS" if code == 0 else "FAIL", exit_code=code,
                              elapsed_seconds=round(time.monotonic()-start, 3), finished_utc=runner.now())
                try:
                    record["case_audit"] = runner.audit_case(out, record)
                except Exception as audit_error:
                    record.update(status="FAIL", error="Case audit failed: " + str(audit_error))
                    raise
                if record["case_audit"]["status"] != "PASS":
                    record["status"] = "FAIL"
                persist()
                if record["status"] != "PASS":
                    raise RuntimeError("Post-route case failed: " + record["name"])
                active.remove(item)
                print("PASS post-route " + record["name"] + ": original command completed and audited", flush=True)
            if active:
                time.sleep(0.2)
    except BaseException as exc:
        # Finish all recovery before acting on a newly arriving signal.
        with deferred_termination():
            reason = str(exc) or type(exc).__name__
            cleanup_errors = []
            for record, process, log, start in active:
                try:
                    stop_process(process)
                except Exception as cleanup_error:
                    # Still stop every other worker if one cleanup fails.
                    record["cleanup_error"] = str(cleanup_error)
                    cleanup_errors.append(record["name"] + ": " + str(cleanup_error))
                finally:
                    log.close()
                    if record.get("status") not in ("PASS", "FAIL"):
                        record.update(status="ABORTED", error="Aborted because another worker/driver failed: " + reason)
                    record.update(exit_code=process.returncode, elapsed_seconds=round(time.monotonic()-start, 3),
                                  finished_utc=runner.now())
            if cleanup_errors:
                result["cleanup_errors"] = cleanup_errors
            for record in result["checks"]:
                if record.get("status") == "PREPARED":
                    record.update(status="ABORTED", error="Not launched because driver failed: " + reason,
                                  exit_code=None, elapsed_seconds=0.0, finished_utc=runner.now())
            persist()
            raise


def execute(runner, out, result, parallel, timeout):
    driver = Path(__file__).resolve()
    result["input_sha256"][str(driver)] = runner.sha(driver)
    # The imported runner already records its own source among the inputs.
    if result["input_sha256"].get(str(RUNNER_PATH)) != FROZEN_RUNNER_SHA256:
        raise ValueError("Frozen runner identity missing from prepared inputs")
    contract = {"sdf_compile_command": copy.deepcopy(result["sdf_compile"]["command"]), "cases": {}}
    for record in result["checks"]:
        name = record["name"]
        contract["cases"][name] = {"command": copy.deepcopy(record["command"]), "cwd": str(out / name),
                                  "file_sha256": {filename: runner.sha(out / name / filename)
                                                  for filename in ("command.json", "sdf_annotation.cmd")}}
    result.update(status="RUNNING", execution_started_utc=runner.now())
    result["parallel_driver"] = {"path": str(driver), "sha256": runner.sha(driver),
                                 "frozen_runner_sha256": FROZEN_RUNNER_SHA256, "max_concurrent_cases": parallel,
                                 "preparation_was_dry_run": True, "command_contract": contract,
                                 "policy": ("Actual commands/cwd frozen after explicit derived-TB source substitution; original arrays and one-region diff retained in poweron_settle; no timing checks suppressed"
                                            if result.get("poweron_settle", {}).get("enabled") else
                                            "Commands/cwd unchanged; no simulator or firmware/testbench timing options adjusted")}

    def persist():
        runner.save(out / "results.json", result)

    def invariant():
        assert_unchanged(runner, out, result, contract)

    try:
        invariant()
        persist()
        run_compile(runner, out, result, timeout, persist)
        invariant()
        run_cases(runner, out, result, parallel, timeout, persist, invariant)
        invariant()
        for record in result["checks"]:
            record["case_audit"] = runner.audit_case(out, record)
            if record["case_audit"]["status"] != "PASS":
                record["status"] = "FAIL"
        result["status"] = "SIMULATION_COMPLETE"
        persist()
        report = runner.audit(out)
        result.update(status=report["status"], finished_utc=runner.now())
        persist()
        return 0 if result["status"] == "PASS" else 1
    except BaseException as exc:
        reason = str(exc) or type(exc).__name__
        for record in result["checks"]:
            if record.get("status") == "PREPARED":
                record.update(status="ABORTED", error="Not launched because driver failed: " + reason,
                              exit_code=None, elapsed_seconds=0.0, finished_utc=runner.now())
        result.update(status="FAIL", error=reason, finished_utc=runner.now())
        persist()
        # The same auditor must reject failure/abort and missing real evidence.
        try:
            report = runner.audit(out)
            if report["status"] == "PASS":
                report.update(status="FAIL", issues=report["issues"] + ["Parallel execution failed: " + reason])
                runner.save(out / "audit.json", report)
        except (OSError, KeyError, ValueError) as audit_error:
            runner.save(out / "audit.json", {"status": "FAIL", "issues": [reason, str(audit_error)]})
        print("FAIL post-route parallel: " + reason, file=sys.stderr, flush=True)
        if isinstance(exc, TerminationRequested):
            return 128 + exc.number
        return 130 if isinstance(exc, KeyboardInterrupt) else 1


def main(argv=None):
    args, forwarded = arguments(list(sys.argv[1:] if argv is None else argv))
    runner = load_runner()
    out = args.out.expanduser().resolve()
    with termination_handlers():
        result = prepare(runner, forwarded, out, args.poweron_settle_ns)
        code = execute(runner, out, result, args.parallel, args.timeout)
    print(json.dumps({"status": result["status"], "results": str(out / "results.json"),
                      "audit": str(out / "audit.json")}, indent=2), flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
