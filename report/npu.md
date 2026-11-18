# 当前NPU

NPU由har_task_engine、har_task_scale、har_npu_core、simple_npu_top及har_weight_store组成，复用16 MAC和两个64B权重bank。原MODE=0专用双层与MODE=1/3单层/续算仍保留。

通用FC使用4×32个INT22累加器。K每次最多64，N最多32，batch最多4；K奇数时屏蔽第二输入lane，N尾部按有效输出处理。原专用FC2仍为4×6个INT22累加器，不扩成通用输出阵列。

har_task_scale用一个22×9乘法器，四次字节乘加完成精确INT22×INT32缩放，54位乘积及舍入保留，再移位饱和。FC量化到INT8的边界在激活融合后仍保留。六种激活为NONE、ReLU、ReLU6、LeakyReLU、Sigmoid、Tanh；后两者共用256项INT8表访问通路。LUT缓存复用32位落地寄存器，默认启用，并非新增256B寄存器阵列。

量化结果按字节打包；末字使用有效掩码，收到AXI B成功响应才报告有效。DMA错误或复位撤销输出、部分和及内部缓冲有效性，已写SRAM字节不自动回滚。

原专用路径仍按FC1的8输出×2输入相位和FC2的6输出×2输入相位执行；FC2只使用共享阵列中的12个MAC。batch=4原固件2700拍，NPU952拍。专用模式的激活、布局及数值语义必须全部匹配，不能只按64→32→6尺寸选择。

[顺序任务ABI](../compiler/TASK_ABI.md)；[兼容FC模式](fc_modes.md)；[本版验收](results/README.md)。
