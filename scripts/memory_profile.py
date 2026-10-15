"""Compile-time main-memory selection; licensed views are local dependencies."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEMORIES = ("reference", "portable-sram", "ra1shd")
ADAPTER_SOURCES = (
    "rtl/memory/chip_sram_2048x32.sv",
    "rtl/memory/my_mainmem_sram.sv",
)


def vendor_model() -> Path:
    path = ROOT / "asic/vendor/RA1SHD_2048x32M8/RA1SHD_2048x32M8.v"
    if not path.is_file():
        raise FileNotFoundError(
            "Licensed SRAM model missing: obtain it through the authorized local "
            "distribution and place it under asic/vendor/RA1SHD_2048x32M8/. "
            "Use portable-sram for public functional tests."
        )
    return path


def sources(memory: str) -> list[Path]:
    if memory not in MEMORIES or memory == "reference":
        raise ValueError("Expected portable-sram or ra1shd memory backend")
    result = [ROOT / name for name in ADAPTER_SOURCES]
    if memory == "ra1shd":
        result.insert(0, vendor_model())
    return result


def soc_target(memory: str) -> tuple[str, str]:
    if memory == "reference":
        return "my_soc_tb", "/my_soc_tb/dut/i_mainmem/INIT_FILE"
    if memory not in MEMORIES:
        raise ValueError("Unknown memory backend")
    return "tb_soc_sram", "/tb_soc_sram/INIT_FILE"


def functional_sim_flags(memory: str) -> str:
    # Zero-delay RTL changes inputs in the same simulation time as CLK.
    # Vendor timing notifiers would corrupt data; STA/SDF is a separate flow.
    return "+notimingchecks " if memory == "ra1shd" else ""
