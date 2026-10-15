# SoC integration

my_soc_top 集成 CV32E40P、AXI、Debug、Boot、SRAM 与 NPU。my_npu_subsystem 保持 MMIO 到 simple_npu_top 的接入边界。原外围字节由 rtl/manifest.json 校验；加速器只选择当前 HAR 实现。
