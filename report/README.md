# 当前设计说明

2026-10-29按用户要求，main已纳入xzx 07af846的共享SRAM事务复位RTL及必要源清单。AXI桥与主存入口同时采用下降沿采样复位，已接受访问完整完成一次。新功能/复位回归通过，但本次RTL的完整四角物理与TT/快/慢SDF仍在xzx独立流程运行；下方旧版通过结果不能证明这次新RTL已完成物理验证。见[本次原因、修改与验证状态](port_request_reset_fix.md)。

当前 xzx 的 SRAM 复位修正版已完成独立EDA与SDF：含PAD **3.795639mm²**，20ns下Setup/Hold **+0.371/+0.019ns**，16组SDF所有阶段动态时序违规0条，半周期路径检查通过。见[修正内容](reset_fix.md)、[新版物理结果](../eda/results/sram_reset_20261027/README.md)和[后仿与main对比](../eda/results/sram_reset_20261027/postsim/README.md)。17条负IOPATH与时间0 PAD模型消息保留为限制。以下为旧版 e15483c 的历史数字。

2026-10-26 后仿补充：16组完整SoC MAXIMUM SDF及无SDF对照通过功能自检，回标error/缺失实例/缺失检查均0，工作窗口动态违规0；复位事件及19条负IOPATH截零限制仍保留。详见[与现有main结果对比](../eda/results/postsim_ntc_20261026/README.md)。下方“未后仿”描述对应原物理交付时点。

最新完成：含PAD **3.79564mm²**，规划85%、实际密度 **67.575%**，20ns下Setup/Hold **+0.226/+0.019ns**，完整34步及三个阶段通过。详见[本轮结果与逐步报告](../eda/results/int8_3p8_20261024/README.md)；下方3.9856mm²为上一轮基线。

上一轮已完成实测：含 PAD **3.9856 mm²**，系统 **20 ns**，最终 Setup/Hold **+0.042 / +0.021 ns**，34/34 及三个阶段通过。详见[本轮结果与逐步报告](../eda/results/int8_20261023/README.md)；SDF 已导出，尚未执行回标后仿。

从 [架构](architecture.md) 理解信号与数据通路，再看 [NPU](npu.md)、[MMIO](mmio.md)、[DMA](dma.md) 和 [SRAM/启动](sram.md)。[开发与验证](development.md) 说明复现功能测试的方法；物理实现从 [EDA 操作指南](../eda/README.md) 开始。

当前真实功能证据：2026-10-23，32 组随机单/双样本批次、12 组训练模型双样本批次共 24 条 UCI 固定输入逐值通过；另有 DMA 错误、重启、复位中断和完整 CPU 自检。完整 SoC 自检 3659 个释放启动密钥后的观测时钟，实际 DMA 读/MAC 重叠 62 拍、写/MAC 重叠 93 拍。该数字含 CPU 软件与检查开销，不是纯 NPU 延迟。

功能仿真不是物理签核；实际 EDA 状态及最终面积以本次上传的 evidence 和最终视图为准，不能引用旧 xzx/rtl 结果。
