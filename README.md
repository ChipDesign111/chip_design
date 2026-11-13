# INT8 HAR 全芯片实现

当前正在将main 266bca3的16-MAC/INT22/取指缓存核心与xzx公共复位、WB修复及完整Lab5流程合并。RTL回归已通过；新一轮物理与TT/Lab5尚待完成。[本轮来源和状态](eda/results/main_266bca3_integration_20261113/README.md)。下列历史结果绑定各自来源，不验证本轮新合并源码。

main 现包含取指行缓冲和固件循环优化。按 SRAM 地址失效取指缓存、缩短 DMA 写响应等待、去除缓存数据阵列复位后，相同训练 HAR 自检 **3510→3462 拍（−1.37%）**；附加 SRAM 写入程序 **7748→4497 拍（−41.96%）**，两者属于不同工作负载。同一套 RTL 上，reuse8 固件在 38 组对照里把完整自检再降低 3.65%，从第一次取指到 NPU DONE 降低 1.23%。完整对照见 [优化报告](report/performance.md)。这次合并没有重做 PNR、SDF 后仿或板测。

2026-11-09 前一轮源码在 `rtl-dev@1eb6462` 上集成 128 B CPU 取指缓存，保留 `CUT_SLV_AX`，并修复单样本 Argmax 的最终值比较。41 组 NPU/DMA 回归、56 项取指检查、4 组完整 SoC 对照和冷启动 Debug 均通过；相同训练固件的 SoC 自检从 **6369→3510 拍（−44.89%）**。详情和后续优化方向见 [本次性能与验证](report/performance.md)、[原始证据索引](report/ifetch_20261109/summary.json)。当前源码尚未重新完成 PNR、SDF 后仿或板测；以下物理和 FPGA 成果均绑定各自的历史版本。

历史 INT22 累加版 `9970d6f` 已完成独立34步 EDA 和最终网表 SDF 后仿：含PAD **3.795639mm²**，20ns下Setup/Hold **+0.032/+0.019ns**，TNS与违规路径均为0；10组MAXIMUM SDF加1组无SDF对照 **11/11功能通过**，回标error/缺失实例/缺失检查均为0，工作窗口与最终复位阶段动态时序违规为0。详见[完整结果](eda/results/int22_20261104/README.md)和[SDF后仿](eda/results/int22_20261104/postsim/README.md)。每个SDF用例的108条初始复位事件及10条负IOPATH截零限制保留。

2026-10-26 后仿补充：16组完整SoC MAXIMUM SDF及无SDF对照通过功能自检，回标error/缺失实例/缺失检查均0，工作窗口动态违规0；复位事件及19条负IOPATH截零限制仍保留。详见[与现有main结果对比](eda/results/postsim_ntc_20261026/README.md)。下方“未后仿”描述对应原物理交付时点。

历史 2026-10-24：含PAD **3.79564mm²**，规划85%、实际密度 **67.575%**，20ns下Setup/Hold **+0.226/+0.019ns**，完整34步及三个阶段通过。详见[本轮结果与逐步报告](eda/results/int8_3p8_20261024/README.md)；下方3.9856mm²为上一轮基线。

上一轮已完成实测：含 PAD **3.9856 mm²**，系统 **20 ns**，最终 Setup/Hold **+0.042 / +0.021 ns**，34/34 及三个阶段通过。详见[本轮结果与逐步报告](eda/results/int8_20261023/README.md)；SDF 已导出，尚未执行回标后仿。

本实现已由 **xzx** 合并至 **main**，开发基线为原 main 267c873。完整 SoC 包含 CV32E40P、AXI、JTAG Debug、8 KiB 主 SRAM 和 64→32→6 NPU。共享 32 乘法器在第一层分两个 16 输出×2 输入相位，在第二层分四个 6 输出×2 输入行相位；两个 64B 权重 tile 缓冲由 DMA 从主 SRAM 按需填充。输入/权重/隐藏激活 INT8，内部累加为 INT22，MMIO 分数仍是32位符号扩展值。当前目标是含 PAD 整颗 Die ≤3.8 mm²。

`rtl-dev` 当前支持最多四样本寄存器批次，并完成 tile 零气泡交接、FC2 四组 48B 粗粒度权重包、W1 尾部 W2 预取、32 乘法器跨层复用和 INT22 内部累加。2026-11-04 归档的 ASIC INT22 版完成了20ns物理实现及SDF后仿；当时的 FPGA 已按 `CUT_SLV_AX` 和 INT22 配置重新综合，20 MHz 时序和 A7-35T 板级自检均通过。FPGA 产物按版本归档，索引见 [FPGA 版本目录](fpga/versions/README.md)，当前状态见 [FPGA 测试报告](fpga/TEST_REPORT.md)。

从本机打包上传到服务器、三个独立阶段和结果回传，直接跟随 [EDA 操作指南](eda/README.md)。服务器从每个上传版本目录的 README.html 开始。结构、启动流程和寄存器见 [设计报告](report/README.md)。

| 目录 | 内容 |
| --- | --- |
| [rtl](rtl/README.md) | 当前完整 SoC 硬件及统一 filelist |
| [eda](eda/README.md) | 正式部署脚本、服务器 EDA 程序、讲义逐步解释及结果分析 |
| [model](model/README.md) | 保留的训练模型、量化参数和整数参考 |
| [test](test/README.md) | 当前 INT8/DMA/启动保护功能回归 |
| [report](report/README.md) | 架构、MMIO、DMA、性能、SRAM 和验证范围 |
| [fpga](fpga/README.md) / [板级测试报告](fpga/TEST_REPORT.md) | Vivado 工程、多镜像 JTAG 装载流程和当前 A7-35T 板上验证结果 |
| [tools](tools/README.md) | 正常工程入口、权重导出和本地依赖管理 |

```bash
python tools/project.py doctor
python test/int8/run.py --count 32 --trained --soc
python tools/export_tiles.py --output tools/local/int8_tiles
python eda/remote.py run
```

本机功能测试使用 Icarus；完整 SoC 另需 ModelSim。当前训练权重读取与 tile 导出无需 NumPy；训练仍使用 model/requirements.txt。EDA 总控需要 Python 3.8+ 与 OpenSSH。大版图、授权库和中间数据库保留服务器；轻量结果回传 lab4 下新目录。

旧分支、旧 RTL 和旧范式记录保存在本地 archives，当前分支只保留更新后实现。第三方源码许可及固定输入来源见 [组件声明](report/THIRD_PARTY_NOTICES.md)。
