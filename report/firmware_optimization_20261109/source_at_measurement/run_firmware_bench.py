"""Compare real CPU programs on one unchanged full-SoC RTL elaboration.

The original tb_soc drives the real CPU and retains all arithmetic self-checks.
Every mode gets identical weights, inputs, configuration and golden data.  The
10 ns functional clock is not a physical timing or signoff frequency claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import firmware
from run_soc_xcelium import ROOT, FIELDS, PASS_RE, elaborate, execute, sha, source_hashes


def input_data(path):
    words = [int(word, 16) for word in path.read_text().split()]
    if len(words) != 2048:
        raise ValueError("Expected complete 8 KiB SRAM image: " + str(path))
    data_start = words[0x1f0c // 4] - 0x80000000
    if data_start not in (0xffc, 0x1000):
        raise ValueError("Unexpected W1 address: " + str(path))
    return data_start, b"".join(word.to_bytes(4, "little") for word in words[data_start // 4:])


def generator_hashes():
    names = ("assembler.py", "firmware.py", "run.py", "run_soc_xcelium.py",
             "run_firmware_bench.py")
    return {"test/int8/" + name: sha(ROOT / "test/int8" / name) for name in names}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Fresh output directory")
    parser.add_argument("--seed", action="append", type=int,
                        help="Repeatable; default 0,1,2,10000")
    parser.add_argument("--mode", action="append", choices=firmware.MODES,
                        help="Repeatable; default all firmware modes")
    parser.add_argument("--reuse-build", type=Path,
                        help="Previous output root; reuse its identical original tb_soc elaboration")
    parser.add_argument("--xrun", default="xrun")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    executable = shutil.which(args.xrun)
    if not executable:
        parser.error("xrun not found; load the EDA environment first")
    seeds = args.seed if args.seed is not None else [0, 1, 2, 10000]
    modes = args.mode if args.mode is not None else list(firmware.MODES)
    if len(set(seeds)) != len(seeds) or len(set(modes)) != len(modes):
        parser.error("Duplicate seeds or modes would overwrite evidence")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    rtl_hashes = source_hashes()
    program_hashes = generator_hashes()
    report = {
        "status": "RUNNING", "clock_period_ns": 10,
        "scope": "Original tb_soc, actual CV32E40P firmware, behavioural SRAM; "
                 "full observed cycles include CPU setup, polling and golden checks",
        "source_sha256": rtl_hashes, "generator_sha256": program_hashes,
        "seeds": seeds, "modes": modes, "cases": [],
        "same_input_data": True,
    }

    def save():
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")

    try:
        # Freeze every input before launching any simulator; code is the only
        # intentionally varying part of each same-seed memory image.
        prepared = []
        for seed in seeds:
            reference = None
            for mode in modes:
                case = out / mode / ("seed_" + str(seed))
                case.mkdir(parents=True)
                firmware.build(case, seed, mode=mode)
                meta = json.loads((case / "firmware_meta.json").read_text())
                data_start, data = input_data(case / "firmware.hex")
                if not 0 < meta["code_bytes"] <= data_start:
                    raise ValueError("Firmware overlaps model data: " + str(case))
                if reference is None:
                    reference = data
                elif reference != data:
                    raise RuntimeError("Same-seed model/input/golden/config differs: " + str(case))
                hashes = {name: sha(case / name) for name in
                          ("firmware.hex", "firmware.S", "firmware_meta.json")}
                info = {
                    "seed": seed, "mode": mode, "batch": meta["batch"],
                    "code_bytes": meta["code_bytes"],
                    "instruction_words": meta["instruction_words"],
                    "input_data_start_offset": data_start,
                    "input_data_sha256": hashlib.sha256(data).hexdigest(),
                    "files_sha256": hashes,
                }
                (case / "input_manifest.json").write_text(json.dumps(info, indent=2) + "\n")
                prepared.append((case, info))
        if args.reuse_build:
            previous = args.reuse_build.resolve()
            prior_report = json.loads((previous / "results.json").read_text())
            if prior_report["status"] != "PASS" or prior_report["source_sha256"] != rtl_hashes:
                raise RuntimeError("Cannot reuse failed or changed RTL/testbench elaboration")
            snapshot = Path(prior_report["snapshot_directory"])
            if not snapshot.is_dir():
                raise RuntimeError("Missing reusable simulator snapshot: " + str(snapshot))
            report["reused_build_from"] = str(previous)
            report["compile_seconds"] = 0
        else:
            snapshot, elapsed = elaborate(executable, out / "build", "tb_soc", args.timeout)
            report["compile_seconds"] = elapsed
        report["snapshot_directory"] = str(snapshot)
        save()
        for case, info in prepared:
            text, elapsed = execute(
                [executable, "-64bit", "-R", "-xmlibdirname", str(snapshot),
                 "-l", str(case / "xrun.log")], case, args.timeout)
            match = PASS_RE.search(text)
            if not match:
                raise RuntimeError("Missing genuine INT8_SOC PASS: " + str(case))
            for name, expected in info["files_sha256"].items():
                if sha(case / name) != expected:
                    raise RuntimeError("Frozen firmware evidence changed: " + str(case / name))
            values = dict(info, **dict(zip(FIELDS, map(int, match.groups()))))
            values["seconds"] = elapsed
            values["log_sha256"] = {name: sha(case / name) for name in ("console.log", "xrun.log")}
            report["cases"].append(values)
            print(json.dumps(values), flush=True)
            save()
        if rtl_hashes != source_hashes() or program_hashes != generator_hashes():
            raise RuntimeError("RTL, testbench or firmware generator changed during experiment")
        baseline = {case["seed"]: case for case in report["cases"] if case["mode"] == "baseline"}
        for case in report["cases"]:
            if case["seed"] in baseline:
                before = baseline[case["seed"]]["observed_cycles"]
                case["cycles_saved_vs_baseline"] = before - case["observed_cycles"]
                case["cycle_reduction_percent"] = round(100.0 * (before - case["observed_cycles"]) / before, 4)
        report["status"] = "PASS"
    except Exception as error:
        report.update(status="FAIL", error=str(error))
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
