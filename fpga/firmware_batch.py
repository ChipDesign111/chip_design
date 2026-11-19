"""Sequential FPGA firmware checks through an existing OpenOCD Tcl service.

--list is offline; --run resets/loads/checks the FPGA through port 6666.
The optional test_all_firmware.gdb wrapper works without embedded Python.
"""
import argparse
import csv
import datetime
import fnmatch
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import struct
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE, BOOT, CYCLES, STATUS = 0x80000000, 0x1003c, 0x10038, 0x80001fe0
PASS, FAIL = 0xc0dec0de, 0xdeadbeef
COUNTERS = {"cycles": 0x0c, "fc1_issue": 0x28, "fc2_issue": 0x2c,
            "overlap_read": 0x34, "overlap_write": 0x38, "overlap_total": 0x1c}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def catalog():
    # Reuse the stdlib-only image/reference/source validation. No PyTorch and
    # no FPGA access is needed here; validate all inputs before resetting a hart.
    spec = importlib.util.spec_from_file_location("_int22_image_validator", HERE / "firmware/validate_images.py")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    legacy = validator.check_legacy()
    suite_dir = HERE / "firmware/suite"
    suite = validator.check_suite(suite_dir)
    cases = []
    for item in legacy["images"]:
        binary = HERE / "firmware" / item["binary_file"]
        image = binary.read_bytes()
        checks = []
        for sample in range(item["batch"]):
            hidden = 0x70000a80 if sample == 0 else 0x70000c40 if sample == 1 else 0x70001200+(sample-2)*64
            scores = 0x70000b00 if sample == 0 else 0x70000c80 if sample == 1 else hidden+0x20
            label = 0x70000008 if sample == 0 else 0x70000c98 if sample == 1 else hidden+0x38
            addresses = [hidden+i*4 for i in range(8)]+[scores+i*4 for i in range(6)]+[label]
            for word, address in enumerate(addresses):
                expected = struct.unpack_from("<I", image, 0x1c00+sample*64+word*4)[0]
                checks.append(dict(address=address, expected=expected, mask=0xffffffff))
        cases.append(dict(name=Path(item["file"]).stem, group="legacy", family="har", backend="npu",
                          batch=item["batch"], binary=binary, firmware_sha256=item["binary_sha256"],
                          checks=checks, halt_pc=item["halt_pc"], pair=None,
                          npu_core_starts=1, npu_batch=item["batch"]))
    for item in suite["images"]:
        directory = suite_dir / item["path"]
        meta = read_json(directory / "board_manifest.json")
        halt_pc = meta.get("halt_pc")
        if halt_pc is None and (directory / "firmware_meta.json").exists():
            halt_pc = read_json(directory / "firmware_meta.json")["labels"]["halt"]
        # CPU packages can place reusable kernels after main's halt label.
        # Their RV32 listings contain one 32-bit instruction per indented line.
        if halt_pc is None and meta["family"] == "har":
            words = 0
            for line in (directory / "firmware.S").read_text().splitlines():
                if line.strip() == "halt:":
                    halt_pc = BASE+words*4
                    break
                if line.startswith("    "):
                    words += 1
            if halt_pc is None or struct.unpack_from("<I", (directory / "firmware.bin").read_bytes(), halt_pc-BASE)[0] != 0x6f:
                raise ValueError("HAR terminal loop changed: "+meta["name"])
        cases.append(dict(name=meta["name"], group="suite", family=meta["family"], backend=meta["backend"],
                          batch=meta["batch"], binary=directory / "firmware.bin",
                          firmware_sha256=item["firmware_sha256"], checks=meta["checks"], halt_pc=halt_pc,
                          tag_address=meta["tag_address"], tag_value=meta["tag_value"],
                          pair="har_b%d" % meta["batch"] if meta["family"] == "har" else "raw_"+meta["case"],
                          npu_core_starts=meta["npu_core_starts"], npu_batch=meta["npu_batch"]))
    return cases


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    action = result.add_mutually_exclusive_group(required=True)
    action.add_argument("--run", action="store_true", help="Run on the FPGA through the existing OpenOCD service")
    action.add_argument("--list", action="store_true", help="Validate/list images without accessing the target")
    result.add_argument("--group", choices=("all", "suite", "legacy"), default="all")
    result.add_argument("--only", action="append", default=[], help="Repeatable image name/glob, e.g. raw_full_b4_*")
    result.add_argument("--out", type=Path, help="Fresh result directory; default is ignored test/int8/runs/fpga_board_TIMESTAMP")
    result.add_argument("--run-seconds", type=float, default=1.0, help="One uninterrupted run per image before halt, default 1 second")
    result.add_argument("--host", default="127.0.0.1", help="OpenOCD Tcl host")
    result.add_argument("--port", type=int, default=6666, help="OpenOCD Tcl port, not GDB port 3333")
    result.add_argument("--command-timeout", dest="remote_timeout", type=int, default=180, help="OpenOCD command timeout in seconds")
    result.add_argument("--fail-fast", action="store_true", help="Stop on the first numerical/incomplete result; transport errors always stop")
    return result


def select_cases(cases, args):
    if not 0 < args.run_seconds <= 60 or args.remote_timeout <= 0:
        raise ValueError("run-seconds must be in (0,60]; remote-timeout must be positive")
    selected = [c for c in cases if args.group == "all" or c["group"] == args.group]
    for pattern in args.only:
        if not any(fnmatch.fnmatchcase(c["name"], pattern) for c in selected):
            raise ValueError("No selected image matches: "+pattern)
    if args.only:
        selected = [c for c in selected if any(fnmatch.fnmatchcase(c["name"], p) for p in args.only)]
    if not selected:
        raise ValueError("No firmware selected")
    return selected


def read_checks(target, checks):
    # Read contiguous aligned runs only. A full 8 KiB readback per image is
    # unnecessary at 10 kHz JTAG, and crossing MMIO holes is avoided.
    addresses = sorted({c["address"] for c in checks})
    observed = {}
    for address in addresses:
        if address in observed:
            continue
        end = address
        while end+4 in addresses and end-address < 252:
            end += 4
        values = target.read_words(address, (end-address)//4+1)
        if len(values) != (end-address)//4+1:
            raise RuntimeError("Incomplete memory read at 0x%08x" % address)
        observed.update({address+i*4: value for i, value in enumerate(values)})
    return [dict(c, actual=observed[c["address"]] & c["mask"]) for c in checks
            if observed[c["address"]] & c["mask"] != c["expected"]]


def execute_case(target, case, args, row):
    image = case["binary"].read_bytes()
    if len(image) != 8192 or hashlib.sha256(image).hexdigest() != case["firmware_sha256"]:
        raise RuntimeError("Image changed after preflight: "+case["name"])
    row["stage"] = "reset"
    target.reset_halt()
    before = target.read_words(BOOT, 1)[0]
    row["boot_before"] = before
    if before != 0:
        raise RuntimeError("Reset did not return to empty Boot state (0x%08x); use a non-preinitialized bitstream" % before)
    row["stage"] = "load"
    target.load(image)
    loaded = target.read_words(BOOT, 1)[0]
    row["boot_loaded"] = loaded
    if loaded != 0x800:
        raise RuntimeError("Incomplete/out-of-order image load: boot=0x%08x" % loaded)
    if target.read_words(STATUS, 1)[0] != struct.unpack_from("<I", image, STATUS-BASE)[0]:
        raise RuntimeError("Loaded completion word does not match this image")
    if target.read_words(BASE, 4) != list(struct.unpack_from("<4I", image)):
        raise RuntimeError("Loaded entry instructions do not match this image")
    if "tag_value" in case and target.read_words(case["tag_address"], 1)[0] != case["tag_value"]:
        raise RuntimeError("Loaded image tag is wrong")
    row["stage"] = "commit"
    target.write_word(BOOT, 0xb007c0de)
    committed = target.read_words(BOOT, 1)[0]
    row["boot_committed"] = committed
    if committed != 0x2800:
        raise RuntimeError("Image commit failed: boot=0x%08x" % committed)
    row["stage"] = "run"
    target.resume(0x10000)
    target.wait(args.run_seconds)
    target.halt()
    row["stage"] = "check"
    row["firmware_status"] = target.read_words(STATUS, 1)[0]
    row["full_soc_cycles"] = target.read_words(CYCLES, 1)[0]
    row["pc"] = target.pc()
    row["last_npu_task"] = {name: target.read_words(0x70000000+offset, 1)[0] for name, offset in COUNTERS.items()}
    errors = []
    if "tag_value" in case and target.read_words(case["tag_address"], 1)[0] != case["tag_value"]:
        errors.append("wrong image tag after execution")
    if row["firmware_status"] != PASS:
        errors.append("firmware FAIL" if row["firmware_status"] == FAIL else
                      "incomplete run; increase --run-seconds (this attempt is not a timing result)")
    if row["firmware_status"] == PASS:
        row["mismatches"] = read_checks(target, case["checks"])
        row["checked_words"] = len(case["checks"])
        if row["mismatches"]:
            errors.append("%d numerical word mismatches" % len(row["mismatches"]))
        if row["full_soc_cycles"] <= 0:
            errors.append("invalid full SoC cycle count")
        if case["halt_pc"] is not None and row["pc"] != case["halt_pc"]:
            errors.append("unexpected terminal DPC 0x%08x (expected 0x%08x)" % (row["pc"],case["halt_pc"]))
        if case["pair"] and target.read_words(BASE+0x1fc0, 1)[0] != 2:
            errors.append("application END marker is missing")
    npu = row["last_npu_task"]
    if case["npu_core_starts"] == 0:
        if any(npu.values()):
            errors.append("pure CPU image has nonzero NPU counters")
    elif (npu["cycles"] <= 0 or npu["fc1_issue"] != 128*case["npu_batch"] or
          npu["fc2_issue"] != (16*case["npu_batch"] if case["family"] == "har" else 0)):
        errors.append("NPU issue counters do not match this image")
    if not max(npu["overlap_read"],npu["overlap_write"]) <= npu["overlap_total"] <= npu["overlap_read"]+npu["overlap_write"]:
        errors.append("invalid DMA/MAC overlap union")
    row.update(status="FAIL" if errors else "PASS", errors=errors, stage="complete", timing_valid=not errors)


def speedups(rows):
    pairs = {}
    for row in rows:
        if row.get("pair") and row["status"] == "PASS":
            pairs.setdefault(row["pair"], {})[row["backend"]] = row
    results = []
    for name, backends in pairs.items():
        accelerated = backends.get("raw", backends.get("npu"))
        cpu = backends.get("cpu")
        if cpu and accelerated:
            results.append(dict(pair=name, cpu_cycles=cpu["full_soc_cycles"],
                                accelerated_cycles=accelerated["full_soc_cycles"],
                                speedup=cpu["full_soc_cycles"]/accelerated["full_soc_cycles"]))
    return results


def save_report(out, report):
    report["speedups"] = speedups(report["cases"])
    report["passed"] = sum(c["status"] == "PASS" for c in report["cases"])
    report["failed"] = sum(c["status"] in ("FAIL", "ERROR") for c in report["cases"])
    report["remaining"] = report["selected"]-len(report["cases"])
    report["updated_at"] = datetime.datetime.now().astimezone().isoformat()
    temp = out / "result.json.tmp"
    temp.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    temp.replace(out / "result.json")
    columns = ["name", "family", "backend", "batch", "status", "timing_valid", "checked_words", "full_soc_cycles",
               "pc", "npu_cycles", "fc1_issue", "fc2_issue", "overlap_read", "overlap_write", "overlap_total", "errors"]
    with (out / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for case in report["cases"]:
            row = {key: case.get(key, "") for key in columns}
            npu = case.get("last_npu_task", {})
            row.update({key: npu.get(key, "") for key in COUNTERS if key != "cycles"})
            row["npu_cycles"] = npu.get("cycles", "")
            row["errors"] = "; ".join(case.get("errors", []))
            if "pc" in case:
                row["pc"] = "0x%08x" % case["pc"]
            writer.writerow(row)
    with (out / "speedups.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=("pair","cpu_cycles","accelerated_cycles","speedup"))
        writer.writeheader();writer.writerows(report["speedups"])
    lines = ["# FPGA firmware batch results", "", "Status: **%s**; PASS %d, FAIL/ERROR %d, remaining %d." %
             (report["status"],report["passed"],report["failed"],report["remaining"]), "",
             "Full SoC cycles: first non-debug fetch after commit through PASS/FAIL; includes firmware checks.",
             "NPU/DMA counters are for the **last hardware task**, not a whole-network sum.", "",
             "| Image | Result | Words checked | Full SoC cycles | Last NPU cycles | DMA/MAC read / write / total |",
             "|---|---|---:|---:|---:|---|"]
    for row in report["cases"]:
        npu = row.get("last_npu_task", {})
        overlap = " / ".join(str(npu.get(key, "-")) for key in ("overlap_read","overlap_write","overlap_total"))
        lines.append("| %s | %s | %s | %s | %s | %s |" % (row["name"],row["status"],row.get("checked_words","-"),
                     row.get("full_soc_cycles","-"),npu.get("cycles","-"),overlap))
    lines += ["", "## Paired full SoC speedups", "", "| Pair | CPU cycles | NPU cycles | CPU / NPU |",
              "|---|---:|---:|---:|"]
    for pair in report["speedups"]:
        lines.append("| %(pair)s | %(cpu_cycles)d | %(accelerated_cycles)d | %(speedup).4fx |" % pair)
    if report.get("error"):
        lines += ["", "Error: "+report["error"]]
    for row in report["cases"]:
        if row.get("errors"):
            lines += ["", "- "+row["name"]+": "+"; ".join(row["errors"])]
    (out / "summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")


def run_batch(target, cases, args, out, emit=print):
    out.mkdir(parents=True, exist_ok=False)
    report = dict(schema=1, status="RUNNING", selected=len(cases), cases=[],
                  environment=target.environment, started_at=datetime.datetime.now().astimezone().isoformat(),
                  resume_address=0x10000, uninterrupted_run_seconds=args.run_seconds,
                  source_sha256={"fpga/firmware_batch.py": sha(Path(__file__)),
                                 "fpga/firmware/image_manifest.json": sha(HERE / "firmware/image_manifest.json"),
                                 "fpga/firmware/suite/suite_manifest.json": sha(HERE / "firmware/suite/suite_manifest.json")})
    save_report(out, report)
    try:
        target.preflight(args.remote_timeout)
        for index, case in enumerate(cases, 1):
            row = {key: case[key] for key in ("name","family","backend","batch","pair","firmware_sha256")}
            row.update(status="RUNNING", errors=[], checked_words=0, timing_valid=False)
            report["cases"].append(row)
            started = time.monotonic()
            emit("[%d/%d] %s: reset, load, run, check" % (index,len(cases),case["name"]))
            try:
                target.begin_log(out / (case["name"]+".log"))
                execute_case(target, case, args, row)
            except KeyboardInterrupt:
                row.update(status="ERROR", errors=["Interrupted by user"])
                raise
            except Exception as error:
                row.update(status="ERROR", errors=[str(error)])
                raise
            finally:
                row["elapsed_seconds"] = round(time.monotonic()-started, 3)
                target.end_log()
                log = out / (case["name"]+".log")
                if log.exists():
                    row["log_sha256"] = sha(log)
                save_report(out, report)
            emit("  %s checked_words=%d full_soc_cycles=%s" % (row["status"],row["checked_words"],row.get("full_soc_cycles","-")))
            if row["errors"]:
                emit("  "+"; ".join(row["errors"]))
            if row["status"] != "PASS" and args.fail_fast:
                break
        report["status"] = "PASS" if len(report["cases"]) == len(cases) and all(c["status"] == "PASS" for c in report["cases"]) else "FAIL"
    except KeyboardInterrupt:
        report.update(status="INTERRUPTED", error="Interrupted by user; target left halted when possible")
    except Exception as error:
        report.update(status="ERROR", error=str(error))
    finally:
        cleanup = target.cleanup()
        if cleanup:
            report["cleanup_errors"] = cleanup
            report["status"] = "ERROR"
        save_report(out, report)
    return report


class OpenOcdTarget:
    def __init__(self, host="127.0.0.1", port=6666):
        self.host, self.port = host, port
        self.environment = "OpenOCD Tcl %s:%d" % (host,port)
        self.sock, self.log = None, None
        self.pending = bytearray()
        self.running, self.broken = False, False

    def command(self, text):
        if self.log:
            self.log.write("> "+text+"\n");self.log.flush()
        # catch makes Tcl/OpenOCD command errors distinguishable from successful
        # empty results. No filenames/user text are interpolated into Tcl.
        request = 'set __int22_rc [catch {%s} __int22_value]; format "%%d\\n%%s" $__int22_rc $__int22_value' % text
        try:
            self.sock.sendall(request.encode("utf-8")+b"\x1a")
            while b"\x1a" not in self.pending:
                part = self.sock.recv(65536)
                if not part:
                    raise ConnectionError("OpenOCD Tcl connection closed")
                self.pending.extend(part)
            end = self.pending.index(0x1a)
            response = bytes(self.pending[:end]).decode("utf-8", errors="replace")
            del self.pending[:end+1]
        except (OSError,KeyboardInterrupt):
            self.broken=True
            raise
        code, separator, result = response.partition("\n")
        if self.log:
            self.log.write(response+"\n");self.log.flush()
        if not separator or code not in ("0","1","2","3","4"):
            self.broken=True
            raise RuntimeError("Invalid OpenOCD Tcl response: "+response)
        if code != "0":
            raise RuntimeError("OpenOCD command failed: "+result)
        return result

    def preflight(self, timeout):
        self.sock=socket.create_connection((self.host,self.port), timeout=10)
        self.sock.settimeout(timeout)
        if self.command("info commands read_memory").strip() != "read_memory":
            raise RuntimeError("The server does not provide OpenOCD read_memory")

    def begin_log(self, path):
        self.log=path.open("w",encoding="utf-8")

    def end_log(self):
        if self.log:
            self.log.close();self.log=None

    def reset_halt(self):
        self.command("reset halt")
        self.command("wait_halt 5000")
        self.running=False

    def load(self, image):
        words=struct.unpack("<2048I",image)
        for start in range(0,2048,32):
            self.command("write_memory 0x%08x 32 {%s}" %
                         (BASE+start*4," ".join("0x%08x" % value for value in words[start:start+32])))

    def read_words(self, address, count):
        response=self.command("read_memory 0x%08x 32 %d" % (address,count))
        values=[int(value,0) & 0xffffffff for value in response.split()]
        if len(values) != count:
            raise RuntimeError("Incomplete read at 0x%08x: %s" % (address,response))
        return values

    def write_word(self, address, value):
        self.command("write_memory 0x%08x 32 {0x%08x}" % (address,value))

    def resume(self, address):
        self.running=True
        self.command("resume 0x%08x" % address)

    def wait(self, seconds):
        time.sleep(seconds)

    def halt(self):
        self.command("halt")
        self.command("wait_halt 5000")
        self.running=False

    def pc(self):
        return int(self.command("dict get [get_reg -force {pc}] pc"),0) & 0xffffffff

    def cleanup(self):
        errors=[]
        try:
            if self.running:
                if self.broken:
                    errors.append("Connection lost while running; target halt could not be confirmed")
                else:
                    self.halt()
        except Exception as error:
            errors.append("Final halt failed: "+str(error))
        self.end_log()
        if self.sock:
            self.sock.close();self.sock=None
        return errors


def main():
    options=parser().parse_args()
    try:
        chosen=select_cases(catalog(),options)
        if options.list:
            for case in chosen:
                print("%s [%s, batch=%d]" % (case["name"],case["backend"],case["batch"]))
            print("%d unique normal firmware images" % len(chosen))
            return 0
        out=options.out.resolve() if options.out else ROOT / "test/int8/runs" / datetime.datetime.now().strftime("fpga_board_%Y%m%d_%H%M%S_%f")
        print("Results: %s" % out,flush=True)
        target=OpenOcdTarget(options.host,options.port)
        result=run_batch(target,chosen,options,out,lambda text:print(text,flush=True))
        if result.get("error"):
            print("Error: "+result["error"],file=sys.stderr)
        print("FPGA_SUITE_%s pass=%d fail=%d remaining=%d\nResults: %s" %
              (result["status"],result["passed"],result["failed"],result["remaining"],out / "summary.md"),flush=True)
        return 0 if result["status"] == "PASS" else 1
    except (Exception,KeyboardInterrupt) as error:
        print("FPGA_SUITE_ERROR: %s" % error,file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
