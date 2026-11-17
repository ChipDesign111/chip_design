"""Independent RAW_GEMV/MMIO/backpressure tests, including legacy mode switches."""
import argparse
import datetime
import hashlib
import json
import random
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def wrap22(value):
    return (value + (1 << 21)) % (1 << 22) - (1 << 21)


def pack(values):
    return [sum((v & 255) << (8 * j) for j, v in enumerate(values[i:i + 4]))
            for i in range(0, len(values), 4)]


def make_case(seed, kind="random", batch=None):
    rng = random.Random(0x726177 + seed)
    batch = batch or 1 + seed % 4
    weights = [[rng.randrange(-128, 128) for _ in range(64)] for _ in range(32)]
    inputs = [[rng.randrange(-128, 128) for _ in range(64)] for _ in range(batch)]
    bias = [rng.randrange(-100000, 100001) for _ in range(32)]
    if kind == "positive_extreme":
        inputs = [[-128] * 64 for _ in range(batch)]
        weights = [[-128] * 64 for _ in range(32)]
        bias = [0] * 32
    elif kind == "negative_extreme":
        inputs = [[-128] * 64 for _ in range(batch)]
        weights = [[127] * 64 for _ in range(32)]
        bias = [0] * 32
    elif kind == "bias_wrap":
        inputs = [[-128 if s % 2 == 0 else 127] * 64 for s in range(batch)]
        weights = [[-128 if o % 2 == 0 else 127] * 64 for o in range(32)]
        bias = [(1 << 21) - 1 if o % 2 == 0 else -(1 << 21) for o in range(32)]
    elif kind == "zero":
        weights = [[0] * 64 for _ in range(32)]
        bias = [0] * 32
    memory = [0] * 2048

    def store(offset, data):
        memory[offset // 4:offset // 4 + len(data)] = [v & 0xffffffff for v in data]

    # Some cases force the first 64-byte descriptor to cross a 4 KiB boundary.
    source_offset = 0xffc if seed % 3 == 0 else 0
    packed_weights = [weights[o][2 * tile + lane]
                      for tile in range(32) for o in range(32) for lane in range(2)]
    store(source_offset, pack(packed_weights))
    for s, vector in enumerate(inputs):
        store(0x1800 + 64 * s, pack(vector))
        # Direct dot products, independent of RTL phases/tile sequencing.
        expected = [wrap22(bias[o] + sum(a * b for a, b in zip(vector, row)))
                    for o, row in enumerate(weights)]
        store(0x1a00 + 128 * s, expected)
    store(0x1900, bias)
    store(0x1f00, [batch, 0x80000000 + source_offset])
    return memory, {"seed": seed, "kind": kind, "batch": batch,
                    "w1_base": hex(0x80000000 + source_offset)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--count", type=int, default=16)
    args = parser.parse_args()
    if args.count < 0:
        parser.error("--count must be nonnegative")
    out = (args.out or HERE / "runs" /
           datetime.datetime.now().strftime("%Y%m%d_%H%M%S_raw_gemv")).resolve()
    out.mkdir(parents=True, exist_ok=False)
    sources = [ROOT / name for name in (
        "rtl/npu/har_weight_store.sv", "rtl/npu/har_npu_core.sv",
        "rtl/npu/simple_npu_top.sv", "rtl/dma/har_dma.sv",
        "test/int8/tb_raw_gemv.sv", "test/int8/run_raw_gemv.py",
        "test/int8/run.py", "model/reference/tile_layout.py",
        "model/export/weights_int8.npz", "model/export/quant_params.json",
        "test/int8/har_uci24.json")]
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sources}
    cases = [make_case(s) for s in range(args.count)]
    cases += [make_case(100 + batch, kind, batch)
              for kind in ("positive_extreme", "negative_extreme", "bias_wrap", "zero")
              for batch in range(1, 5)]
    for index, (memory, _) in enumerate(cases):
        (out / f"case_{index}.hex").write_text(
            "".join(f"{v:08x}\n" for v in memory), encoding="ascii")
    from run import make_case as legacy_case
    (out / "legacy.hex").write_text(
        "".join(f"{v:08x}\n" for v in legacy_case(10000)), encoding="ascii")
    commands = [
        ("compile", ["iverilog", "-g2012", "-s", "tb_raw_gemv", "-o",
                     str(out / "test.vvp")] + [str(p) for p in sources[:5]]),
        ("simulation", ["vvp", str(out / "test.vvp"), "+DIR=" + out.as_posix(),
                        "+COUNT=" + str(len(cases))]),
    ]
    for name, command in commands:
        result = subprocess.run(command, cwd=out, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=180)
        (out / (name + ".log")).write_bytes(result.stdout)
        output = result.stdout.decode(errors="replace")
        if result.returncode or re.search(r"FATAL|RAW_GEMV_FAIL", output):
            raise RuntimeError(output[-12000:])
    if f"RAW_GEMV_PASS cases={len(cases)}" not in output:
        raise RuntimeError("Missing RAW regression completion marker")
    if any(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != value
           for name, value in hashes.items()):
        raise RuntimeError("Sources changed during RAW regression")
    report = {"status": "PASS", "source_sha256": hashes,
              "raw_cases": [metadata for _, metadata in cases],
              "raw_values_checked": sum(32 * metadata["batch"] for _, metadata in cases),
              "legacy_switch_case": "trained seed 10000; hidden/scores/class checked",
              "protocol_checks": ["reset defaults", "invalid mode and index", "latched batch",
                                  "raw selection ready", "ACK", "busy protection",
                                  "DMA read/write/RLAST faults", "reset in transfer",
                                  "consecutive RAW_INDEX/ACK", "consecutive RAW_INDEX/START",
                                  "RAW-legacy-RAW", "no W2 DMA", "INT22 storage"],
              "scope": "Icarus synthetic AXI RTL functional regression; no physical timing claim"}
    (out / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(output)
    print("Results: " + str(out))


if __name__ == "__main__":
    main()
