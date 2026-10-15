# Full-system verification

The imported my_soc_tb remains in verification/lab3/soc and drives the real CV32E40P integration. Firmware is generated under build/sw or build/real_model and supplied through INIT_FILE.

SoC backends run original CPU images, synthetic accelerator programs and trained-model self-checks. A true SRAM PASS magic is required; zero simulator exit alone is insufficient.

Run `python project.py test --suite soc --vsim /path/to/vsim` and `--suite model-soc`. No replacement CPU BFM is used.

tb_soc_sram is the independent test top for portable-sram / ra1shd main memory. It preloads via actual memory ports during reset and passively observes CPU status writes. It does not use a vendor array hierarchy. Original fixtures remain frozen. See [SRAM](../../docs/sram.md).
