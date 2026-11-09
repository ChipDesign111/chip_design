"""Verify that optimized CPU firmware still rejects corrupted golden results.

Reuse a successful, identical original tb_soc elaboration. Each negative case
changes one golden word in the last sample, including the score loop's tail;
the real CPU must report its numerical self-check failure.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from run_soc_xcelium import sha, source_hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", required=True, type=Path)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--seed", type=int, default=10000)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--xrun", default="xrun")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    executable = shutil.which(args.xrun)
    if not executable:
        parser.error("xrun not found; load the EDA environment first")
    benchmark = args.benchmark.resolve()
    previous = json.loads((benchmark / "results.json").read_text())
    sources = source_hashes()
    if previous["status"] != "PASS" or previous["source_sha256"] != sources:
        raise RuntimeError("Expected a passing benchmark on identical RTL and testbench")
    origin = benchmark / args.mode / ("seed_" + str(args.seed))
    record = next(case for case in previous["cases"]
                  if case["seed"] == args.seed and case["mode"] == args.mode)
    if sha(origin / "firmware.hex") != record["files_sha256"]["firmware.hex"]:
        raise RuntimeError("Reference firmware differs from passing benchmark")
    words = [int(word, 16) for word in (origin / "firmware.hex").read_text().split()]
    batch = record["batch"]
    golden = 0x1c00 + (batch - 1) * 64
    snapshot = Path(previous["snapshot_directory"])
    if not snapshot.is_dir():
        raise RuntimeError("Missing elaboration: " + str(snapshot))
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {"status": "RUNNING", "source_sha256": sources,
              "benchmark": str(benchmark), "mode": args.mode, "seed": args.seed,
              "reference_firmware_sha256": sha(origin / "firmware.hex"),
              "runner_sha256": sha(Path(__file__)), "cases": []}
    try:
        for name, offset in (("hidden_last", golden + 28),
                             ("score_tail", golden + 52),
                             ("class_last", golden + 56)):
            case = out / name
            case.mkdir()
            corrupt = words.copy()
            corrupt[offset // 4] ^= 1
            assert sum(a != b for a, b in zip(words, corrupt)) == 1
            (case / "firmware.hex").write_text("".join("%08x\n" % word for word in corrupt))
            with (case / "console.log").open("wb") as log:
                process = subprocess.run(
                    [executable, "-64bit", "-R", "-xmlibdirname", str(snapshot),
                     "-l", str(case / "xrun.log")], cwd=str(case), stdout=log,
                    stderr=subprocess.STDOUT, timeout=args.timeout)
            text = (case / "console.log").read_text(errors="replace")
            if ("CPU numerical self-check failed" not in text or
                    "INT8_SOC PASS" in text or process.returncode == 0):
                raise RuntimeError("Corruption did not produce expected CPU rejection: " + name)
            result = {"case": name, "status": "EXPECTED_FAILURE", "sample": batch - 1,
                      "sram_offset": hex(offset), "original_word": hex(words[offset // 4]),
                      "corrupted_word": hex(corrupt[offset // 4]),
                      "simulator_exit_code": process.returncode,
                      "files_sha256": {file: sha(case / file) for file in
                                       ("firmware.hex", "console.log", "xrun.log")}}
            report["cases"].append(result)
            print(json.dumps(result), flush=True)
        if source_hashes() != sources:
            raise RuntimeError("RTL or original testbench changed during negative tests")
        report["status"] = "PASS"
    except Exception as error:
        report.update(status="FAIL", error=str(error))
        raise
    finally:
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
