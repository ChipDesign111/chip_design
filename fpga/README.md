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
