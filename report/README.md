# 当前设计说明

main 现包含取指行缓冲、缩短后的 DMA 写响应，以及同一套 RTL 上的 reuse8 固件。共享 SRAM 事务复位仍在 RTL 里。下面的面积、SDF 和 FPGA 数字都属于各自的归档版本，不是这次合并新做的物理签核。本轮缓存一致性与 DMA 优化的匹配数据、测试入口和面积/时序比较见 [优化报告](performance.md)。

2026-11-09 前一轮：源码已集成 CPU 取指缓存并修复单样本 Argmax；功能回归及同固件拍数对照见 [性能报告](performance.md) 和 [证据索引](ifetch_20261109/summary.json)。以下较早日期的面积、SDF、FPGA 数据仅代表对应归档版本。

2026-10-29：为满足 A7-35T 容量，NPU 最大 batch 调整为 4 个样本共享一个权重 tile，输入、累加器和输出全部驻留寄存器，没有新增 NPU 内部 SRAM。32 组随机单/双/四样本和 6 组训练模型四样本批次逐值通过，完整 CPU SoC batch=4 自检通过。

同日完成调度优化：移除 tile 间固定交接气泡；FC2 改为每 8 行、每行 6 输出打包为 48 B，并在 W1 尾部跨层预取 W2。共享 MAC bank 最终收为 32 个乘法器，FC1 分两个 16 输出相位。上一版把 FC2 改为每拍 2 输入行，并把 FINISH 分类改为每拍比较一个候选；该版本地回归通过，batch=1/2/4 NPU 为 1401/1431/1541 拍，完整 SoC 为 6369 拍。2026-11-04 归档版本把内部累加器收窄为 INT22，并完成该版本的同源 34 步 EDA 和 MAXIMUM SDF 后仿：NPU 面积降至 0.896961 mm²，20 ns 下 Setup/Hold WNS 为 +0.032/+0.019 ns，后仿 11/11 功能通过且工作窗口时序事件为 0。详见 [INT22 完整结果](../eda/results/int22_20261104/README.md) 和 [SDF 后仿](../eda/results/int22_20261104/postsim/README.md)。

本页下方的旧面积、时序和 SDF 数字属于 batch=2 的历史物理结果。当前 batch=4 + INT22 的同源 34 步结果见 [INT22 验证记录](int22_validation.json)，不能与下方旧 PPA 混用。

当前 xzx 的 SRAM 复位修正版已完成独立EDA与SDF：含PAD **3.795639mm²**，20ns下Setup/Hold **+0.371/+0.019ns**，16组SDF所有阶段动态时序违规0条，半周期路径检查通过。见[修正内容](reset_fix.md)、[新版物理结果](../eda/results/sram_reset_20261027/README.md)和[后仿与main对比](../eda/results/sram_reset_20261027/postsim/README.md)。17条负IOPATH与时间0 PAD模型消息保留为限制。以下为旧版 e15483c 的历史数字。

2026-10-26 后仿补充：16组完整SoC MAXIMUM SDF及无SDF对照通过功能自检，回标error/缺失实例/缺失检查均0，工作窗口动态违规0；复位事件及19条负IOPATH截零限制仍保留。详见[与现有main结果对比](../eda/results/postsim_ntc_20261026/README.md)。下方“未后仿”描述对应原物理交付时点。

最新完成：含PAD **3.79564mm²**，规划85%、实际密度 **67.575%**，20ns下Setup/Hold **+0.226/+0.019ns**，完整34步及三个阶段通过。详见[本轮结果与逐步报告](../eda/results/int8_3p8_20261024/README.md)；下方3.9856mm²为上一轮基线。

上一轮已完成实测：含 PAD **3.9856 mm²**，系统 **20 ns**，最终 Setup/Hold **+0.042 / +0.021 ns**，34/34 及三个阶段通过。详见[本轮结果与逐步报告](../eda/results/int8_20261023/README.md)；SDF 已导出，尚未执行回标后仿。

从 [架构](architecture.md) 理解信号与数据通路，再看 [NPU](npu.md)、[MMIO](mmio.md)、[DMA](dma.md)、[性能对比](performance.md) 和 [SRAM/启动](sram.md)。[开发与验证](development.md) 说明复现功能测试的方法；物理实现从 [EDA 操作指南](../eda/README.md) 开始。

功能回归使用 `python test/int8/run.py --count 32 --trained --soc`。当前 INT22 版本的随机参考已覆盖 22 位补码边界和回绕；训练数据按 6 个四样本批次覆盖 24 条 UCI 固定输入。本次集成的完整 SoC 已在 Xcelium 复验，详情见上述性能报告。

功能仿真不是物理签核；实际 EDA 状态及最终面积以本次上传的 evidence 和最终视图为准，不能引用旧 xzx/rtl 结果。
