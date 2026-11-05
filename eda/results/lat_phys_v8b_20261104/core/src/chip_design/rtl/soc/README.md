# SoC 集成

my_soc_top 保留六个信号端口、四发起端/四目标端 AXI、CPU 和 Debug。NPU 自动描述符连接 har_dma_axi；Boot 控制器在 SRAM 完整装载提交后才放行 CPU 取指。my_npu_subsystem 负责 NPU MMIO 与 DMA CSR 选择。见 [架构](../../report/architecture.md)。
