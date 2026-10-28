# 当前 INT8 NPU

har_npu_core：64+6 个 INT8 乘法器、1120 位乘积流水、最多 8 个寄存器驻留样本、共享重定标、分类；tile 就绪时零气泡交接。
har_weight_store：两个 64B bank；FC1 一 bank 一 tile，FC2 每 bank 打包 8 个 6B 逻辑 tile。
simple_npu_top：MMIO、自动 DMA 描述符、W1/W2 分域发布、W1 尾部 W2 预取、1/2/8 样本配置与保护。

文件和使用方法见 [NPU](../../report/npu.md)、[MMIO](../../report/mmio.md)。
