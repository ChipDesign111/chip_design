"""Check portable RAM inference and macro connectivity without vendor views."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yosys", default=shutil.which("yosys"))
    args = parser.parse_args()
    if not args.yosys:
        parser.error("Yosys not found")
    out = ROOT / "build/synthesis/memory"
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    for backend in ("portable", "macro"):
        netlist = out / (backend + ".json")
        commands = []
        flags = ""
        if backend == "macro":
            commands.append("read_verilog -sv -lib asic/ra1shd_blackbox.sv")
            flags = "-DCHIP_USE_RA1SHD "
        commands.extend([
            "read_verilog -sv " + flags + "rtl/memory/chip_sram_2048x32.sv rtl/memory/my_mainmem_sram.sv",
            "hierarchy -check -top my_mainmem", "proc", "opt", "memory_dff",
            "memory_collect", "opt_clean", "check -assert",
            'write_json "' + netlist.as_posix() + '"',
        ])
        script = out / (backend + ".ys")
        script.write_text("\n".join(commands) + "\n", encoding="utf-8")
        with (out / (backend + ".log")).open("w", encoding="utf-8") as log:
            subprocess.run([args.yosys, "-Q", "-T", "-s", str(script)], cwd=ROOT,
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
        design = json.loads(netlist.read_text())
        cells = [cell for module in design["modules"].values() for cell in module.get("cells", {}).values()]
        assert not any("latch" in cell["type"].lower() for cell in cells)
        memories = [cell for cell in cells if cell["type"] == "$mem_v2"]
        macros = [cell for cell in cells if cell["type"] == "RA1SHD_2048x32M8"]
        if backend == "portable":
            assert len(memories) == 1 and not macros
            params = memories[0]["parameters"]
            assert int(params["SIZE"], 2) == 2048 and int(params["WIDTH"], 2) == 32
            assert int(params["RD_CLK_ENABLE"], 2) == 1
            results[backend] = {"bits": 65536, "synchronous_read_ports": 1, "pass": True}
        else:
            assert len(macros) == 1 and not memories
            connections = macros[0]["connections"]
            assert {name: len(bits) for name, bits in connections.items()} == {
                "CLK": 1, "CEN": 1, "WEN": 4, "A": 11, "D": 32, "OEN": 1, "Q": 32}
            assert connections["OEN"] == ["0"]
            results[backend] = {"blackbox_instances": 1, "pass": True}
    results["tool"] = subprocess.check_output([args.yosys, "-V"], text=True).strip()
    results["scope"] = "Generic inference/connectivity only; no vendor library, timing or physical signoff"
    (out / "summary.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results), flush=True)


if __name__ == "__main__":
    main()
