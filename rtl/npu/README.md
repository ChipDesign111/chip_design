# 当前 INT8 NPU

har_npu_core：共享 64 个 INT8 乘法器、最多 4 个寄存器驻留样本、共享重定标、分类；FC1 映射为 32 输出×2 lane，FC2 映射为 6 输出×8 输入行。
har_weight_store：两个 64B bank；FC1 一 bank 一 tile，FC2 每 bank 是一组 8 行×6 输出的 48B 权重包。
simple_npu_top：MMIO、自动 DMA 描述符、W1/W2 分域发布、W1 尾部 W2 预取、1/2/4 样本配置与保护。

文件和使用方法见 [NPU](../../report/npu.md)、[MMIO](../../report/mmio.md)。
