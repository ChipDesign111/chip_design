# Bare-metal verification software

Current executable generation is provided by scripts/build_har_firmware.py and scripts/build_model_firmware.py. The RV32I images execute on the real CV32E40P and compare hidden/score/class and cycle counters; no cross compiler is required for this path.

Original startup/linker material and C/hex fixtures are retained for provenance and compatibility. A production C driver and GCC/ELF build chain are not implemented. Reserved include/drivers/tests boundaries do not imply existing software.

SRAM budgets: [memory budget](../docs/memory-budget.md). CPU test scope: [verification](../docs/verification.md).
