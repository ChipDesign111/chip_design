# SoC integration

my_soc_top 集成 CV32E40P、AXI、Debug、Boot、SRAM 与 NPU。my_npu_subsystem 保持 MMIO 到 simple_npu_top 的接入边界。原外围字节由 rtl/manifest.json 校验；加速器只选择当前 HAR 实现。

DMA integration adds a fourth AXI initiator and routes its CSR through the NPU window. Tagged DMA writes are admitted while untagged host writes are blocked during DMA activity. See [DMA](../../report/dma.md).
