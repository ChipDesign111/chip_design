"""Full-SoC RTL regression with Xcelium; save raw logs and source/firmware hashes.

Run from an environment where xrun is on PATH. For a matched comparison, pass
the first run's output directory as --firmware-dir on the second checkout.
The existing testbench uses a 10 ns clock and behavioural SRAM. Its cycle
counter covers execution after image commit, including CPU golden checks;
these are functional RTL measurements, not timing-signoff frequency results.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
FIELDS = (
    "observed_cycles", "hardware_soc_cycles", "npu_cycles",
    "fc1_issue_cycles", "fc2_issue_cycles", "dma_read_overlap", "dma_write_overlap",
)
PASS_RE = re.compile(
    r"INT8_SOC PASS cycles=(\d+) hw_soc_cycles=(\d+) npu_cycles=(\d+) "
    r"fc1_issue_cycles=(\d+) fc2_issue_cycles=(\d+) "
    r"DMA_read_MAC_overlap=(\d+) DMA_write_MAC_overlap=(\d+)"
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    paths = sorted(p for p in (ROOT / "rtl").rglob("*") if p.is_file())
    paths += [ROOT / "test/int8/tb_soc.sv", ROOT / "test/int8/tb_debug_cold.sv"]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}


def execute(command, directory, timeout):
    start = time.monotonic()
    with (directory / "console.log").open("wb") as output:
        result = subprocess.run(command, cwd=str(directory), stdout=output,
                                stderr=subprocess.STDOUT, timeout=timeout)
    text = (directory / "console.log").read_text(errors="replace")
    errors = re.findall(r"^.*(?:\*[EF],|FATAL|TIMEOUT).*$", text, re.M)
    if result.returncode or errors:
        raise RuntimeError("%s failed: exit=%d %s" %
                           (directory, result.returncode, errors[-5:]))
    return text, round(time.monotonic() - start, 3)


def elaborate(executable, output, top, timeout):
    output.mkdir()
    sources = []
    for line in (ROOT / "rtl/filelist.f").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("+incdir+"):
            sources.append("+incdir+" + str(ROOT / line[8:]))
        else:
            sources.append(str(ROOT / line))
    sources.append(str(ROOT / "test/int8" / (top + ".sv")))
    filelist = output / "sources.f"
    filelist.write_text("\n".join(sources) + "\n")
    snapshot = output / "xcelium.d"
    _, elapsed = execute(
        [executable, "-64bit", "-sv", "-timescale", "1ns/1ps", "-f", str(filelist),
         "-top", top, "-elaborate", "-xmlibdirname", str(snapshot),
         "-l", str(output / "xrun.log"), "+notimingchecks", "-nospecify"],
        output, timeout,
    )
    return snapshot, elapsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Fresh output directory")
    parser.add_argument("--seed", type=int, action="append", help="Repeatable; default 0,1,2,10000")
    parser.add_argument("--firmware-dir", type=Path,
                        help="Reuse seed_N/firmware.hex from another run for exact comparisons")
    parser.add_argument("--debug-cold", action="store_true", help="Also verify debug entry before image commit")
    parser.add_argument("--xrun", default="xrun", help="Xcelium executable")
    parser.add_argument("--timeout", type=int, default=600, help="Seconds per simulator invocation")
    args = parser.parse_args()
    executable = shutil.which(args.xrun)
    if not executable:
        parser.error("xrun not found; first load the EDA environment")
    seeds = args.seed if args.seed is not None else [0, 1, 2, 10000]
    if len(set(seeds)) != len(seeds):
        parser.error("Duplicate seeds would overwrite evidence")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    manifest = source_hashes()
    report = {
        "status": "RUNNING", "clock_period_ns": 10,
        "scope": "Full SoC RTL with behavioural SRAM; cycles after firmware commit include CPU self-checks",
        "source_sha256": manifest, "cases": [],
    }

    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")

    try:
        snapshot, elapsed = elaborate(executable, out / "build", "tb_soc", args.timeout)
        report["compile_seconds"] = elapsed
        for seed in seeds:
            case = out / ("seed_" + str(seed))
            case.mkdir()
            if args.firmware_dir:
                origin = args.firmware_dir.resolve() / case.name
                for filename in ("firmware.hex", "firmware.S"):
                    path = origin / filename
                    if filename == "firmware.hex" or path.exists():
                        shutil.copyfile(path, case / filename)
            else:
                from firmware import build
                build(case, seed)
            firmware_hash = sha(case / "firmware.hex")
            text, elapsed = execute(
                [executable, "-64bit", "-R", "-xmlibdirname", str(snapshot),
                 "-l", str(case / "xrun.log")], case, args.timeout,
            )
            match = PASS_RE.search(text)
            if not match:
                raise RuntimeError("Missing genuine INT8_SOC PASS: " + str(case))
            if firmware_hash != sha(case / "firmware.hex"):
                raise RuntimeError("Firmware changed during simulation: " + str(case))
            values = dict(zip(FIELDS, map(int, match.groups())))
            values.update(seed=seed, firmware_sha256=firmware_hash, seconds=elapsed)
            report["cases"].append(values)
            print(json.dumps(values), flush=True)
            save()
        if args.debug_cold:
            snapshot, _ = elaborate(executable, out / "debug_build", "tb_debug_cold", args.timeout)
            case = out / "debug_cold"
            case.mkdir()
            text, _ = execute(
                [executable, "-64bit", "-R", "-xmlibdirname", str(snapshot),
                 "-l", str(case / "xrun.log")], case, args.timeout,
            )
            match = re.search(
                r"DEBUG_COLD PASS halt_cycles=(\d+) boot_ready=0 pc=([0-9a-f]+) dm_halted=1", text,
            )
            if not match:
                raise RuntimeError("Missing genuine DEBUG_COLD PASS: " + str(case))
            report["debug_cold"] = {"status": "PASS", "halt_cycles": int(match[1]), "pc": match[2]}
            print(json.dumps(report["debug_cold"]), flush=True)
        if manifest != source_hashes():
            raise RuntimeError("RTL or testbench source changed during regression")
        report["status"] = "PASS"
    except Exception as error:
        report.update(status="FAIL", error=str(error))
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
