# 当前 INT8 NPU

har_npu_core：64+6 个 INT8 乘法器、双样本累加、共享重定标、分类。
har_weight_store：两个 64B tile bank，无完整模型常驻 bank。
simple_npu_top：MMIO、自动 DMA 描述符、缓冲发布/释放与保护。

文件和使用方法见 [NPU](../../report/npu.md)、[MMIO](../../report/mmio.md)。
