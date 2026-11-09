"""Run existing memory/alias workloads with the selected optimized firmware."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test/int8"))
import firmware
import firmware_workloads
from run_firmware_bench import generator_hashes
from run_soc_xcelium import FIELDS, PASS_RE, execute, sha, source_hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=firmware.MODES, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--reuse-build", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    previous = json.loads((args.reuse_build / "results.json").read_text())
    assert previous["status"] == "PASS" and previous["source_sha256"] == source_hashes()
    report = {"status": "RUNNING", "source_sha256": source_hashes(),
              "generator_sha256": generator_hashes(), "mode": args.mode,
              "wrapper_sha256": sha(Path(__file__)), "cases": []}
    original = firmware.build

    def selected_build(run, seed=10000):
        return original(run, seed, mode=args.mode)

    try:
        firmware.build = selected_build
        for workload in ("scratch_128", "code_patch_alias_byte"):
            case = out / workload / "seed_10000"
            case.mkdir(parents=True)
            firmware_workloads.build(case, workload, 10000)
            hashes = {name: sha(case / name) for name in
                      ("firmware.hex", "firmware.S", "firmware_meta.json")}
            text, elapsed = execute(
                [shutil.which("xrun"), "-64bit", "-R", "-xmlibdirname",
                 previous["snapshot_directory"], "-l", str(case / "xrun.log")], case, 600)
            match = PASS_RE.search(text)
            assert match, workload
            assert all(sha(case / name) == value for name, value in hashes.items())
            values = dict(zip(FIELDS, map(int, match.groups())))
            values.update(workload=workload, seconds=elapsed, files_sha256=hashes)
            report["cases"].append(values)
            print(json.dumps(values), flush=True)
        assert report["source_sha256"] == source_hashes()
        assert report["generator_sha256"] == generator_hashes()
        report["status"] = "PASS"
    except Exception as error:
        report.update(status="FAIL", error=str(error))
        raise
    finally:
        firmware.build = original
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
