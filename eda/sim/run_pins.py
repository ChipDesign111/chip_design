#!/usr/bin/env python3
"""Xcelium external JTAG boot test shared by RTL and synthesized SoC netlists.

Python 3.8+, standard library only. Source the course EDA environment first.
Firmware is pre-generated and checked against firmware/manifest.json hashes.
The runner never supplies a DUT hierarchical initialization or force command.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def checked_file(value):
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ValueError("Missing input file: " + str(path))
    return path


def escaped(value):
    return str(value).replace("\\", "/").replace('"', '\\"')


def rtl_filelist(memory, sram_model, destination):
    lines = []
    source_paths = []
    for original in (ROOT / "rtl/filelist.f").read_text().splitlines():
        line = original.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("+incdir+"):
            lines.append("+incdir+" + str((ROOT / line[8:]).resolve()))
        elif line.startswith("+"):
            lines.append(line)
        else:
            path = checked_file(ROOT / line)
            source_paths.append(path)
            lines.append(str(path))
    if memory == "ra1shd":
        if not sram_model:
            raise ValueError("RTL ra1shd requires --sram-model pointing to the licensed Verilog model")
        path = checked_file(sram_model)
        lines = ["+define+CHIP_USE_RA1SHD", str(path)] + lines
        source_paths.append(path)
    source_paths = sorted(set(source_paths) | {p for p in (ROOT / "rtl").rglob("*") if p.is_file()})
    destination.write_text("\n".join(lines) + "\n")
    return source_paths


def read_text(path):
    return path.read_text(errors="replace") if path.exists() else ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("rtl", "gate", "sdf"), required=True)
    parser.add_argument("--only", choices=("synthetic", "cpu", "dma", "corrupt_download"), action="append",
                        help="Repeat to select cases; default synthetic + dma")
    parser.add_argument("--memory", choices=("portable-sram", "ra1shd"), default="ra1shd")
    parser.add_argument("--sram-model", help="Licensed SRAM .v used by RTL ra1shd or mapped netlist")
    parser.add_argument("--netlist", help="Complete mapped my_soc_top Verilog netlist")
    parser.add_argument("--library", action="append", default=[], help="Additional cell model source; repeat as needed")
    parser.add_argument("--sdf", help="SDF file (.sdf or .sdf.gz); mandatory in sdf mode")
    parser.add_argument("--sdf-corner", choices=("MINIMUM", "TYPICAL", "MAXIMUM"), default="MAXIMUM")
    parser.add_argument("--sys-period", type=float, default=20.0, help="System period in ns")
    parser.add_argument("--tck-period", type=float, default=100.0, help="JTAG TCK period in ns")
    parser.add_argument("--boots", type=int, default=2)
    parser.add_argument("--quiet-cycles", type=int, default=100000)
    parser.add_argument("--max-polls", type=int, default=2000)
    parser.add_argument("--timeout", type=int, default=7200, help="Wall time per case in seconds")
    parser.add_argument("--watchdog-ns", type=float, default=250000000.0)
    parser.add_argument("--out", type=Path, help="Fresh output directory; old results are never overwritten")
    parser.add_argument("--xrun", default="xrun")
    parser.add_argument("--xmsdfc", default="xmsdfc", help="Cadence SDF compiler used before command-file annotation")
    parser.add_argument("--xrun-arg", action="append", default=[], help="Extra Xcelium argument; use --xrun-arg=VALUE")
    parser.add_argument("--dry-run", action="store_true", help="Prepare commands/manifests without claiming simulation PASS")
    args = parser.parse_args()
    if min(args.sys_period, args.tck_period, args.boots, args.quiet_cycles, args.max_polls, args.timeout, args.watchdog_ns) <= 0:
        parser.error("Periods, boot count, quiet cycles, limits, and timeouts must be positive")
    if args.mode != "rtl" and not args.netlist:
        parser.error("gate/sdf mode requires --netlist")
    if args.mode == "sdf" and not args.sdf:
        parser.error("sdf mode requires --sdf")
    if args.mode != "sdf" and args.sdf:
        parser.error("--sdf is accepted only in sdf mode")
    if args.mode == "rtl" and (args.netlist or args.library):
        parser.error("--netlist and --library are gate/sdf inputs")
    if args.mode == "sdf" and any(re.search(r"notiming|nospecify|delay_mode_zero|sdf_no", flag, re.I) for flag in args.xrun_arg):
        parser.error("SDF checks cannot disable specify timing or timing checks")
    selected = args.only or ["synthetic", "dma"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = (args.out or ROOT / "eda/work" / ("pins_" + args.mode + "_" + stamp)).resolve()
    if out.exists() and any(out.iterdir()):
        parser.error("Output directory is not empty: " + str(out))
    out.mkdir(parents=True, exist_ok=True)
    if args.mode == "rtl":
        source_paths = rtl_filelist(args.memory, args.sram_model, out / "rtl.f")
        compile_args = ["-f", str(out / "rtl.f")]
    else:
        netlist = checked_file(args.netlist)
        libs = [checked_file(path) for path in args.library]
        if args.sram_model:
            libs.append(checked_file(args.sram_model))
        if not libs:
            parser.error("gate/sdf mode requires the standard-cell and SRAM models via --library/--sram-model")
        source_paths = [netlist] + libs
        compile_args = [str(path) for path in source_paths]
    source_paths.append(HERE / "tb_soc_pins.sv")
    source_paths.append(HERE / "run_pins.py")
    sdf = None
    sdf_compile = None
    if args.sdf:
        sdf_input = checked_file(args.sdf)
        source_paths.append(sdf_input)
        sdf = out / "annotate.sdf"
        if sdf_input.suffix == ".gz":
            with gzip.open(str(sdf_input), "rb") as reader, sdf.open("wb") as writer:
                for block in iter(lambda: reader.read(1024 * 1024), b""):
                    writer.write(block)
        else:
            sdf.write_bytes(sdf_input.read_bytes())
        compiled_sdf = out / "annotate.sdf.X"
        sdf_compile_command = [args.xmsdfc, "-64bit", str(sdf), "-output", str(compiled_sdf)]
        sdf_compile = {"command": sdf_compile_command, "status": "PREPARED"}
        if not args.dry_run:
            with (out / "sdf_compile.log").open("wb") as log:
                process = subprocess.run(sdf_compile_command, cwd=str(out), stdout=log, stderr=subprocess.STDOUT,
                                         timeout=args.timeout)
            sdf_compile.update(exit_code=process.returncode,
                               status="PASS" if process.returncode == 0 and compiled_sdf.is_file() else "FAIL")
            if compiled_sdf.is_file():
                sdf_compile["compiled_sha256"] = digest(compiled_sdf)
            (out / "sdf_compile.json").write_text(json.dumps(sdf_compile, indent=2) + "\n")
            if sdf_compile["status"] != "PASS":
                raise RuntimeError("SDF compilation failed; inspect " + str(out / "sdf_compile.log"))
    manifest_path = HERE / "firmware/manifest.json"
    firmware = json.loads(manifest_path.read_text())
    source_paths.append(manifest_path)
    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode, "sys_period_ns": args.sys_period, "tck_period_ns": args.tck_period,
        "scope": "JTAG pins only: TAP/DMI/SBA, 2048-word download and readback, real CPU firmware checks, fresh reset boots",
        "functional_timing_checks_disabled": args.mode != "sdf",
        "sdf_corner": args.sdf_corner if sdf else None,
        "sdf_annotation_method": "xmsdfc + xrun -sdf_cmd_file" if sdf else None,
        "sdf_compile": sdf_compile,
        "limitations": ["No internal hierarchy probes; DMA physical AXI beat/burst counts are covered by the separate RTL protocol test",
                        "No physical board, power, DFT, or LVS validation"],
        "sources_sha256": {str(path): digest(path) for path in source_paths}, "checks": [],
        "status": "PREPARED" if args.dry_run else "RUNNING"
    }
    summary_path = out / "results.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    for name in selected:
        case = firmware["cases"]["synthetic" if name == "corrupt_download" else name]
        image = checked_file(HERE / "firmware" / case["image"])
        if digest(image) != case["sha256"]:
            raise RuntimeError("Firmware hash mismatch: " + str(image))
        words = image.read_text().split()
        if len(words) != 2048 or any(not re.fullmatch(r"[0-9a-fA-F]{8}", word) for word in words):
            raise RuntimeError("Expected exactly 2048 known 32-bit firmware words")
        dest = out / name
        dest.mkdir()
        command = [args.xrun, "-64bit", "-sv", "-timescale", "1ns/1ps"] + compile_args
        command += [str(HERE / "tb_soc_pins.sv"), "-top", "tb_soc_pins", "-l", str(dest / "xrun.log")]
        if args.mode != "sdf":
            command += ["+notimingchecks", "-nospecify"]
        else:
            # TSMC's NTC/RECREM branches supply delayed D/CP/CDN signals and
            # the combined recovery/removal checks emitted by Genus. Enable
            # negative propagation-delay handling; do not clip those delays
            # or disable any specify/timing checks.
            command += ["+define+NTC+RECREM", "-negdelay"]
        parameters = {
            "INIT_FILE": '"' + escaped(image) + '"', "CLK_PERIOD_NS": args.sys_period,
            "TCK_PERIOD_NS": args.tck_period, "BOOTS": args.boots,
            "CORRUPT_WORD": 7 if name == "corrupt_download" else -1,
            "EXPECT_DMA": int(name == "dma"), "BENCHMARK": int(name in ("cpu", "dma")),
            "QUIET_CYCLES": args.quiet_cycles, "MAX_POLLS": args.max_polls,
            "WATCHDOG_NS": args.watchdog_ns,
        }
        if sdf:
            # Xcelium 21.09 ignores a variable-argument $sdf_annotate during
            # elaboration (CUSSTI). Use its documented compiled-SDF command
            # file instead; leave the testbench SDF_FILE parameter empty.
            sdf_command_file = dest / "sdf_annotation.cmd"
            sdf_command_file.write_text(
                'COMPILED_SDF_FILE = "' + escaped(compiled_sdf) + '",\n'
                'SCOPE = tb_soc_pins.dut,\n'
                'LOG_FILE = "' + escaped(dest / "sdf_annotation.log") + '",\n'
                'MTM_CONTROL = "' + args.sdf_corner + '";\n')
            command += ["-sdf_cmd_file", str(sdf_command_file), "-sdfstats", str(dest / "sdf_unannotated.log")]
        for key, value in parameters.items():
            command += ["-defparam", "tb_soc_pins." + key + "=" + str(value)]
        command += args.xrun_arg
        record = {"name": name, "command": command, "image_sha256": digest(image),
                  "firmware_checks": case["checks"], "status": "PREPARED"}
        if sdf:
            record.update(sdf_command_file=str(sdf_command_file), sdf_command_sha256=digest(sdf_command_file),
                          sdf_command_raw=sdf_command_file.read_text())
        summary["checks"].append(record)
        (dest / "command.json").write_text(json.dumps(command, indent=2) + "\n")
        summary_path.write_text(json.dumps(summary, indent=2) + "\n")
        if args.dry_run:
            print("PREPARED " + name + " (not executed)", flush=True)
            continue
        started = time.monotonic()
        log_path = dest / "console.log"
        try:
            with log_path.open("wb") as console:
                process = subprocess.run(command, cwd=str(dest), stdout=console, stderr=subprocess.STDOUT,
                                         timeout=args.timeout)
            log = read_text(log_path)
            evidence = [line for line in log.splitlines() if line.startswith(("PIN_", "SOC_PINS"))]
            errors = re.findall(r"^.*\*[EF],.*$", log, re.M)
            if name == "corrupt_download":
                ok = process.returncode != 0 and "SRAM verify word=7" in log and "SOC_PINS PASS" not in log and "PIN_CPU_PASS" not in log
            else:
                marker = "SOC_PINS PASS downloaded_words=2048 verified_words=2048 boots=" + str(args.boots)
                boots = re.findall(r"PIN_CPU_PASS run=(\d+) magic=c0dec0de", log)
                ok = process.returncode == 0 and marker in log and boots == [str(n) for n in range(args.boots)] and not errors
            if sdf:
                annotation_log = read_text(dest / "sdf_annotation.log")
                timing_problems = re.findall(r"^.*(?:\*W,(?:SDF\w+|TIM\w+)|timing violation).*$", log + "\n" + annotation_log, re.M | re.I)
                record["sdf_annotation_log_bytes"] = len(annotation_log)
                record["sdf_timing_problems"] = timing_problems
                statistics = re.findall(r"^.*No\. of (?:Pathdelays|Tchecks).*Annotated.*$", log, re.M)
                counts = [int(value) for value in re.findall(r"Annotated\s*=\s*[\d.]+%\s*\((\d+)/\d+\)", "\n".join(statistics))]
                record["sdf_annotation_statistics_raw"] = statistics
                record["sdf_annotated_elements"] = sum(counts)
                record["sdf_unannotated_log_bytes"] = (dest / "sdf_unannotated.log").stat().st_size if (dest / "sdf_unannotated.log").exists() else None
                ok = ok and bool(annotation_log) and not timing_problems and sum(counts) > 0 and "Annotation completed successfully" in log
            record.update(status="PASS" if ok else "FAIL", exit_code=process.returncode,
                          elapsed_seconds=round(time.monotonic() - started, 3), evidence=evidence, simulator_errors=errors)
            if not ok:
                raise RuntimeError("Pin-level " + args.mode + " case failed: " + name + "; inspect " + str(log_path))
            print("PASS " + args.mode + " " + name + ": " + evidence[-1], flush=True)
        except Exception as exc:
            record.update(status="FAIL", error=str(exc), elapsed_seconds=round(time.monotonic() - started, 3))
            summary["status"] = "FAIL"
            summary_path.write_text(json.dumps(summary, indent=2) + "\n")
            raise
        summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    for path in source_paths:
        if digest(path) != summary["sources_sha256"][str(path)]:
            raise RuntimeError("Input changed during run: " + str(path))
    summary["status"] = "PREPARED" if args.dry_run else "PASS"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(str(summary_path), flush=True)


if __name__ == "__main__":
    main()
