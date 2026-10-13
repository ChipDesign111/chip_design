# Integration extensions

Reserved boundary; no independent system top is implemented here. The compiled top is platform/course_soc/soc/rtl/my_soc_top.sv, and the bridge is my_npu_subsystem.sv.

The accelerator's MMIO wrapper is rtl/npu/har/simple_npu_top.sv. Avoid duplicating a CPU or top to modify an accelerator. Integration changes follow [ADR 0001](../../docs/adr/0001-fixed-platform-boundary.md).
