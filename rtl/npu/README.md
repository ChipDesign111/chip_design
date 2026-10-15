# Tiled MLP NPU

har_dot_tile：乘法/累加流水；har_weight_store：38 个同步权重 bank；har_npu_core：两级调度、双缓冲、ReLU/量化/Argmax；simple_npu_top：MMIO 包装。

只保留当前 64→32→6 实现。接口及周期变更需要同步参考、固件生成与测试。见 [设计](../../report/npu.md) 和 [寄存器](../../report/mmio.md)。
