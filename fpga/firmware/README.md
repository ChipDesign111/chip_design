# FPGA firmware image

`model_selftest_dma.hex` is the current 24-row HAR self-test using the DMA
parameter/input loader. It is a 2048-word, 32-bit memory image consumed by
`fpga_top` through the `FPGA_INIT_FILE` parameter.

Generate the CPU and DMA variants from the repository root with:

```sh
export CHIP_TEST_RUN="$PWD/test/2026-10-22/runs/fpga_firmware"
python test/2026-10-15/scripts/export_real_model.py
python -c "import sys; sys.path.insert(0, 'test/2026-10-15/scripts'); from build_model_firmware import build_model; build_model(use_dma=False, benchmark=True); build_model(use_dma=True, benchmark=True)"
```

The checked-in image is `model_selftest_dma.hex`, SHA-256
`54c32dca604287846adf60fca7c0aa9a5125c69dc96dc69ecea6df03bce3689f`.
