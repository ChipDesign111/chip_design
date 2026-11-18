"""Fixed-seed single-batch NPU timing probe with deterministic AXI backpressure."""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run import make_case  # noqa: E402


def execute(command, cwd, name):
    result = subprocess.run(
        [str(value) for value in command],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=300,
    )
    (cwd / f"{name}.log").write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"{name} failed\n{result.stdout[-5000:]}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=10000)
    parser.add_argument("--batch", type=int, action="append", choices=(1, 2, 3, 4),
                        help="Repeatable; default 1,2,4")
    parser.add_argument("--out", type=Path, help="Fresh output directory")
    args = parser.parse_args()

    stamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
    run = (args.out or HERE / "runs" / stamp / "perf").resolve()
    run.mkdir(parents=True, exist_ok=False)
    memory = make_case(args.seed)
    batches = args.batch or (1, 2, 4)
    if len(set(batches)) != len(batches):
        parser.error("Duplicate batches would overwrite evidence")
    if any(batch > memory[0x1f08 // 4] for batch in batches):
        parser.error("Batch must select a prefix of the selected input fixture")
    sources = [
        "rtl/npu/har_weight_store.sv", "rtl/npu/har_npu_core.sv",
        "rtl/npu/simple_npu_top.sv", "rtl/dma/har_dma.sv", "test/int8/tb_tiled_dma.sv",
    ]
    inputs = sources + ["test/int8/perf.py", "test/int8/run.py", "test/int8/har_uci24.json",
                        "model/reference/tile_layout.py", "model/export/weights_int8.npz",
                        "model/export/quant_params.json"]
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    source = {name: sha(ROOT/name) for name in inputs}
    (run/"source_manifest.json").write_text(json.dumps(source, indent=2)+"\n")
    results = {}
    report = dict(status="RUNNING", seed=args.seed, results=results, source_sha256=source,
                  clock_period_ns=10,
                  scope="Standalone NPU+DMA with deterministic synthetic AXI backpressure; not CPU/SoC end-to-end",
                  timing="NPU hardware START/DONE interval; excludes testbench MMIO configuration and output checks",
                  serial_speedup_definition="batch * batch1_cycles / batch_cycles; NPU interval throughput gain, not CPU speedup")
    def save():
        (run/"result.json").write_text(json.dumps(report, indent=2)+"\n")
    save()
    for batch in batches:
        case = run / f"batch{batch}"
        case.mkdir()
        case_memory = memory.copy()
        case_memory[0x1F08 // 4] = batch
        (case / "case_0.hex").write_text(
            "".join(f"{value:08x}\n" for value in case_memory), encoding="utf-8"
        )

    executable = run / "test.vvp"
    execute(
        ["iverilog", "-g2012", "-s", "tb_tiled_dma", "-o", executable]
        + [ROOT / source for source in sources],
        run,
        "compile",
    )

    for batch in batches:
        case = run / f"batch{batch}"
        output = execute(
            ["vvp", executable, f"+DIR={case}", "+COUNT=1"], run, f"batch{batch}"
        )
        match = re.search(
            r"CASE 0 PASS cycles=(\d+) fc1=(\d+) fc2=(\d+)"
            r" read_overlap=(\d+) write_overlap=(\d+)",
            output,
        )
        if not match:
            raise RuntimeError(f"Missing batch{batch} timing line")
        cycles, fc1, fc2, read_overlap, write_overlap = map(int, match.groups())
        if fc1 != 128*batch or fc2 != 16*batch:
            raise RuntimeError("Unexpected current INT22/16-MAC issue counts")
        if "INT8_TILED_DMA PASS cases=1 accumulator_bits=22" not in output:
            raise RuntimeError("Missing complete standalone functional PASS")
        results[str(batch)] = {
            "cycles": cycles,
            "cycles_per_sample": cycles / batch,
            "fc1_issue_cycles": fc1,
            "fc2_issue_cycles": fc2,
            "read_mac_overlap": read_overlap,
            "write_mac_overlap": write_overlap,
            "useful_macs": batch*2240,
            "macs_per_cycle": batch*2240/cycles,
            "evidence_sha256": {"case_0.hex": sha(case/"case_0.hex"),
                                "log": sha(run/f"batch{batch}.log")},
        }
        save()

    if any(sha(ROOT/name) != digest for name, digest in source.items()):
        raise RuntimeError("Sources changed during performance probe")
    if "1" in results:
        for batch, row in results.items():
            row["speedup_vs_serial_batch1"] = int(batch)*results["1"]["cycles"]/row["cycles"]
    report.update(status="PASS", compile_log_sha256=sha(run/"compile.log"))
    save()
    print(json.dumps(results, indent=2))
    print(f"Results: {run}")


if __name__ == "__main__":
    main()
