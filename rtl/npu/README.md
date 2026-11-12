# 当前 INT8 NPU

har_npu_core：共享 32 个 INT8 乘法器、最多 4 个寄存器驻留样本、22 位有符号内部累加、共享重定标和顺序分类；FC1 每阶段映射为 16 输出×2 lane，FC2 每阶段映射为 6 输出×2 输入行。FC1 在每个 tile 边界为全部样本预装两个 8 位输入 lane，避免乘法器前的 tile 索引高扇出选择；就绪 bank 直接交接时预装下一 tile，不增加 ISSUE 周期。首 tile 偏置/反馈选择由 32 个保留的逐输出 flag 控制，避免一个网络驱动整个累加器阵列。重定标拆分为 sample/8 输出组选择、8 选 1 和 22×16 乘法饱和三级，保持每拍处理一个输出，FC1 层末增加两拍排空。FINISH 每拍只做一次 22 位有符号比较，每样本五拍；32 位 MMIO score 由内部值符号扩展。
har_weight_store：两个 64B bank；FC1 一 bank 一 tile，FC2 每 bank 是一组 8 行×6 输出的 48B 权重包。
simple_npu_top：MMIO、自动 DMA 描述符、W1/W2 分域发布、W1 尾部 W2 预取、1/2/4 样本配置与保护。

文件和使用方法见 [NPU](../../report/npu.md)、[MMIO](../../report/mmio.md)。
