# 当前设计说明

从 [架构](architecture.md) 理解信号与数据通路，再看 [NPU](npu.md)、[MMIO](mmio.md)、[DMA](dma.md) 和 [SRAM/启动](sram.md)。[开发与验证](development.md) 说明复现功能测试的方法；物理实现从 [EDA 操作指南](../eda/README.md) 开始。

当前真实功能证据：2026-10-23，32 组随机单/双样本批次、12 组训练模型双样本批次共 24 条 UCI 固定输入逐值通过；另有 DMA 错误、重启、复位中断和完整 CPU 自检。完整 SoC 自检 7341 个释放启动密钥后的观测时钟，实际 DMA 读/MAC 与 DMA 写/MAC 各重叠 62 拍。该数字含 CPU 软件与检查开销，不是纯 NPU 延迟。

功能仿真不是物理签核；实际 EDA 状态及最终面积以本次上传的 evidence 和最终视图为准，不能引用旧 xzx/rtl 结果。
