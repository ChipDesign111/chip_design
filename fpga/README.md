# FPGA final project

The Vivado 2019.1 workspace is `final_project/final_project.xpr` and targets
an Artix-7 `xc7a35tcsg324-1`.

`fpga_top.sv` keeps the Lab6 port names and pin plan. It instantiates the
current HAR SoC at 50 MHz and initializes the 8 KiB main memory from
`firmware/model_selftest_dma.hex`.

LED behavior:

- `led_locked`: MMCM locked.
- `led_heartbeat`: normal heartbeat, solid for PASS, fast blink for FAIL.
- `led_tck`: JTAG clock activity.

The project can be refreshed from the repository root with:

```powershell
D:\Xilinx\Vivado\2019.1\bin\vivado.bat -mode batch `
  -source fpga\configure_final_project.tcl
```

`build_final_project.tcl` uses normal Vivado project runs. `build_direct.tcl`
is a fallback for environments where `launch_runs` cannot create its Windows
job wrapper.

The project uses the `Flow_RuntimeOptimized` synthesis strategy and preserves
the RTL hierarchy for faster bring-up iterations. Use `reset_runs.tcl` after a
canceled or interrupted run before launching synthesis again.

## A7-35T resource limit

The runtime-optimized build still does not fit `xc7a35tcsg324-1`. Post-
synthesis utilization is approximately 39,841 LUTs versus 20,800 available;
after `opt_design` the placer still reports 35,510 required LUT sites. The NPU
subsystem alone uses about 27,600 LUTs. Block RAM is lightly used (2/50), so the
current limitation is logic and multiplier parallelism rather than memory.

This device therefore requires either a larger FPGA or a lower-parallelism
FPGA NPU implementation. The current 39/59-cycle compute contract cannot be
preserved on the 35T without a substantially different packed-DSP
implementation.
