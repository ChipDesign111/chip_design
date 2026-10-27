# 当前设计说明

2026-10-28：NPU 已扩展为最多 8 个样本共享一个权重 tile，输入、累加器和输出全部驻留寄存器，没有新增 NPU 内部 SRAM。32 组随机单/双/八样本和 3 组训练模型八样本批次逐值通过，完整 CPU SoC batch=8 自检通过。

同日完成两级调度优化：移除 tile 间固定交接气泡；FC2 改为每 8 个逻辑 tile 打包为 48 B，并在 W1 尾部跨层预取 W2。固定基准下 batch=8 从 2025 拍降至 1808 拍，详见[性能对比](performance.md)。

本页下方面积、时序和 SDF 数字属于 batch=2 的历史物理结果。batch=8 将 FC1 累加器从 2×32×32 bit 增至 8×32×32 bit，改变了网表、面积和时序，旧 PPA 不能用于当前 RTL；必须重新综合、布局布线和签发对应证据。

当前 xzx 的 SRAM 复位修正版已完成独立EDA与SDF：含PAD **3.795639mm²**，20ns下Setup/Hold **+0.371/+0.019ns**，16组SDF所有阶段动态时序违规0条，半周期路径检查通过。见[修正内容](reset_fix.md)、[新版物理结果](../eda/results/sram_reset_20261027/README.md)和[后仿与main对比](../eda/results/sram_reset_20261027/postsim/README.md)。17条负IOPATH与时间0 PAD模型消息保留为限制。以下为旧版 e15483c 的历史数字。

2026-10-26 后仿补充：16组完整SoC MAXIMUM SDF及无SDF对照通过功能自检，回标error/缺失实例/缺失检查均0，工作窗口动态违规0；复位事件及19条负IOPATH截零限制仍保留。详见[与现有main结果对比](../eda/results/postsim_ntc_20261026/README.md)。下方“未后仿”描述对应原物理交付时点。

最新完成：含PAD **3.79564mm²**，规划85%、实际密度 **67.575%**，20ns下Setup/Hold **+0.226/+0.019ns**，完整34步及三个阶段通过。详见[本轮结果与逐步报告](../eda/results/int8_3p8_20261024/README.md)；下方3.9856mm²为上一轮基线。

上一轮已完成实测：含 PAD **3.9856 mm²**，系统 **20 ns**，最终 Setup/Hold **+0.042 / +0.021 ns**，34/34 及三个阶段通过。详见[本轮结果与逐步报告](../eda/results/int8_20261023/README.md)；SDF 已导出，尚未执行回标后仿。

从 [架构](architecture.md) 理解信号与数据通路，再看 [NPU](npu.md)、[MMIO](mmio.md)、[DMA](dma.md)、[性能对比](performance.md) 和 [SRAM/启动](sram.md)。[开发与验证](development.md) 说明复现功能测试的方法；物理实现从 [EDA 操作指南](../eda/README.md) 开始。

当前功能证据使用 `python test/int8/run.py --count 32 --trained --soc`。随机批次同时覆盖 batch=1、2、8；训练数据按 3 个八样本批次覆盖 24 条 UCI 固定输入。完整 SoC 通过 batch=8 CPU/MMIO 自检，并保持真实 DMA 读写与 MAC 重叠。

功能仿真不是物理签核；实际 EDA 状态及最终面积以本次上传的 evidence 和最终视图为准，不能引用旧 xzx/rtl 结果。
