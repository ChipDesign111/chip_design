"""Fixed-seed single-batch NPU timing probe with deterministic AXI backpressure."""
import argparse
import datetime
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
    args = parser.parse_args()

    run = HERE / "runs" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S") / "perf"
    run.mkdir(parents=True)
    memory = make_case(args.seed)
    batches = (1, 2, 4)
    for batch in batches:
        case = run / f"batch{batch}"
        case.mkdir()
        case_memory = memory.copy()
        case_memory[0x1F08 // 4] = batch
        (case / "case_0.hex").write_text(
            "".join(f"{value:08x}\n" for value in case_memory), encoding="utf-8"
        )

    executable = run / "test.vvp"
    sources = [
        "rtl/npu/har_weight_store.sv",
        "rtl/npu/har_npu_core.sv",
        "rtl/npu/simple_npu_top.sv",
        "rtl/dma/har_dma.sv",
        "test/int8/tb_tiled_dma.sv",
    ]
    execute(
        ["iverilog", "-g2012", "-s", "tb_tiled_dma", "-o", executable]
        + [ROOT / source for source in sources],
        run,
        "compile",
    )

    results = {}
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
        results[str(batch)] = {
            "cycles": cycles,
            "cycles_per_sample": cycles / batch,
            "fc1_issue_cycles": fc1,
            "fc2_issue_cycles": fc2,
            "read_mac_overlap": read_overlap,
            "write_mac_overlap": write_overlap,
        }

    (run / "result.json").write_text(
        json.dumps({"seed": args.seed, "results": results}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(results, indent=2))
    print(f"Results: {run}")


if __name__ == "__main__":
    main()
