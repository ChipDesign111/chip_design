"""Exercise the main-memory adapter against portable or local vendor models."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools.workspace import WORK, TEST_ROOT
sys.path.insert(0, str(ROOT))
from tools.memory_profile import sources
from tools.simulation import RESULTS, execute, tool


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory", choices=("portable-sram", "ra1shd"), default="portable-sram")
    parser.add_argument("--iverilog")
    parser.add_argument("--vvp")
    args = parser.parse_args()
    inputs = sources(args.memory)
    out = WORK / "memory" / args.memory
    out.mkdir(parents=True, exist_ok=True)
    image = out / "mainmem.vvp"
    name = "sram_" + args.memory
    flags = ["-DCHIP_USE_RA1SHD"] if args.memory == "ra1shd" else []
    result_path = WORK / "results" / (name + ".json")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        execute(name + "_compile", [tool("iverilog", args.iverilog), "-g2012", *flags,
            "-s", "tb_mainmem_sram", "-o", image, *inputs,
            ROOT / "test/2026-10-20/rtl/tb_mainmem_sram.sv"])
        execute(name, [tool("vvp", args.vvp), image], cwd=out,
                marker="SRAM_UNIT PASS reads=6128 writes=4064 masks=16")
    finally:
        result_path.write_text(json.dumps(RESULTS, indent=2) + "\n", encoding="utf-8")
    print("ALL SRAM TESTS PASS", flush=True)


if __name__ == "__main__":
    main()
