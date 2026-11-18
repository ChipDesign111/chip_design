"""Verify cold debug and guarded ROM boot on the full SoC using real JTAG/DMI.

The synthetic SRAM program writes PASS immediately, so any pre-commit escape
is observable. Bulk loading alone uses the existing SBA master test boundary;
halt/resume, status, DPC and progbuf commands traverse the real JTAG transport.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

from assembler import Assembler

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Fresh output directory")
    parser.add_argument("--vsim", default="vsim")
    parser.add_argument("--soc-rtl", type=Path, help="Override SoC integration for a negative control")
    parser.add_argument("--boot-rtl", type=Path, help="Override bootram for a negative control")
    parser.add_argument("--expect-failure", choices=("RESET_STATE_MISREPORTED", "UNCOMMITTED_SRAM_FETCH",
                                                    "DEBUG_ABSTRACT_COMMAND_FAILED"))
    args = parser.parse_args()
    if args.expect_failure and not (args.soc_rtl or args.boot_rtl):
        parser.error("Negative controls require an explicit RTL override")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    overrides = {"rtl/soc/my_soc_top.sv": args.soc_rtl,
                 "rtl/memory/bootram.sv": args.boot_rtl}
    sources, paths = [], [Path(__file__).resolve(), HERE / "assembler.py"]
    for line in (ROOT / "rtl/filelist.f").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("+incdir+"):
            sources.append("+incdir+" + (ROOT / line[8:]).as_posix())
        else:
            path = (overrides.get(line) or (ROOT / line)).resolve()
            sources.append(path.as_posix())
            paths.append(path)
    paths += [p for p in (ROOT / "rtl").rglob("*.svh")]
    for name in ("tb_boot_debug.sv", "tb_debug_cold.sv"):
        paths.append(HERE / name)
        sources.append((HERE / name).as_posix())
    paths.append(ROOT / "rtl/filelist.f")
    hashes = {str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p): sha(p)
              for p in sorted(set(paths))}
    program = Assembler()
    program.li(5, 0x80001fe0)
    program.li(6, 0xc0dec0de)
    program.sw(6, 5)
    program.label("halt")
    program.jump("halt")
    program.resolve()
    if program.labels["halt"] != 0x80000014:
        raise AssertionError("Test payload terminal PC changed")
    image = program.words + [0] * (2048 - len(program.words))
    (out / "firmware.hex").write_text("".join("%08x\n" % w for w in image))
    (out / "soc.f").write_text("\n".join(sources) + "\n")
    tops = [("tb_boot_debug", "BOOT_DEBUG_PASS"),
            ("tb_boot_preinitialized", "BOOT_PREINITIALIZED_PASS"),
            ("tb_debug_cold", "DEBUG_COLD PASS")]
    commands = ["onerror {quit -code 1}", "onbreak {resume}",
                "vlib work", "vmap work work", "vlog -sv -f soc.f"]
    for top, _ in tops[:1] if args.expect_failure else tops:
        commands += ["vsim -suppress 12110 -voptargs=+acc -onfinish stop work." + top,
                     "run -all"]
        if top != "tb_debug_cold":
            commands += ["set passed [examine -radix unsigned /%s/passed]" % top,
                         "if {$passed != 1} {quit -code 3}"]
        commands.append("quit -sim")
    commands.append("quit -code 0")
    (out / "run.do").write_text("\n".join(commands) + "\n")
    report = dict(status="RUNNING", scope="Full SoC RTL, real JTAG/DMI, behavioural SRAM; no board/timing claim",
                  source_sha256=hashes, firmware_sha256=sha(out / "firmware.hex"),
                  expected_failure=args.expect_failure)
    start = time.monotonic()
    try:
        with (out / "soc.log").open("wb") as log:
            result = subprocess.run([args.vsim, "-c", "-do", "do run.do"], cwd=out,
                                    stdout=log, stderr=subprocess.STDOUT, timeout=300)
        text = (out / "soc.log").read_text(errors="replace")
        errors = re.search(r"FATAL:|# \*\* (?:Fatal|Error):|TIMEOUT", text)
        cases = re.findall(r"BOOT_DEBUG_CASE_PASS (\w+)", text)
        if args.expect_failure:
            if not errors or not re.search(r"\*\* Fatal: " + args.expect_failure + r"\b", text):
                raise RuntimeError("Negative control did not fail for the expected reason: " + text[-3000:])
            expected_cases = {"RESET_STATE_MISREPORTED": 0, "UNCOMMITTED_SRAM_FETCH": 3,
                              "DEBUG_ABSTRACT_COMMAND_FAILED": 8}
            if len(cases) != expected_cases[args.expect_failure]:
                raise RuntimeError("Negative control failed at the wrong stage: " + str(cases))
            report.update(status="EXPECTED_FAILURE", reason=args.expect_failure, completed_cases=cases)
        else:
            if result.returncode or errors or any(marker not in text for _, marker in tops):
                raise RuntimeError("Boot/debug regression failed: " + text[-4000:])
            if len(cases) != 10:
                raise RuntimeError("Missing boot/debug cases: " + str(cases))
            report.update(status="PASS", cases=cases, preinitialized_resets=2, legacy_cold_halt=True)
        for name, digest in hashes.items():
            if sha(ROOT / name) != digest:
                raise RuntimeError("Source changed during boot/debug run: " + name)
        report["log_sha256"] = sha(out / "soc.log")
        print("BOOT_DEBUG_CHECK_%s %s" % (report["status"], out), flush=True)
    except Exception as error:
        report.update(status="FAIL", error=str(error))
        raise
    finally:
        report["seconds"] = round(time.monotonic() - start, 3)
        (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
