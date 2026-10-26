# INT8 HAR 全芯片实现

2026-10-26 后仿补充：16组完整SoC MAXIMUM SDF及无SDF对照通过功能自检，回标error/缺失实例/缺失检查均0，工作窗口动态违规0；复位事件及19条负IOPATH截零限制仍保留。详见[与现有main结果对比](eda/results/postsim_ntc_20261026/README.md)。下方“未后仿”描述对应原物理交付时点。

最新完成：含PAD **3.79564mm²**，规划85%、实际密度 **67.575%**，20ns下Setup/Hold **+0.226/+0.019ns**，完整34步及三个阶段通过。详见[本轮结果与逐步报告](eda/results/int8_3p8_20261024/README.md)；下方3.9856mm²为上一轮基线。

上一轮已完成实测：含 PAD **3.9856 mm²**，系统 **20 ns**，最终 Setup/Hold **+0.042 / +0.021 ns**，34/34 及三个阶段通过。详见[本轮结果与逐步报告](eda/results/int8_20261023/README.md)；SDF 已导出，尚未执行回标后仿。

本实现已由 **xzx** 合并至 **main**，开发基线为原 main 267c873。完整 SoC 包含 CV32E40P、AXI、JTAG Debug、8 KiB 主 SRAM 和 64→32→6 NPU。第一层 2 输入×32 输出、第二层 1×6；两个 64B 权重 tile 缓冲由 DMA 从主 SRAM 按需填充。输入/权重/隐藏激活 INT8，偏置/累加/分数 INT32。当前目标是含 PAD 整颗 Die ≤3.8 mm²。

从本机打包上传到服务器、三个独立阶段和结果回传，直接跟随 [EDA 操作指南](eda/README.md)。服务器从每个上传版本目录的 README.html 开始。结构、启动流程和寄存器见 [设计报告](report/README.md)。

| 目录 | 内容 |
| --- | --- |
| [rtl](rtl/README.md) | 当前完整 SoC 硬件及统一 filelist |
| [eda](eda/README.md) | 正式部署脚本、服务器 EDA 程序、讲义逐步解释及结果分析 |
| [model](model/README.md) | 保留的训练模型、量化参数和整数参考 |
| [test](test/README.md) | 当前 INT8/DMA/启动保护功能回归 |
| [report](report/README.md) | 架构、MMIO、DMA、SRAM 和验证范围 |
| [fpga](fpga/README.md) | main 更新带来的 Vivado 工程，已更换当前固件；本轮验收在 ASIC 服务器 |
| [tools](tools/README.md) | 正常工程入口、权重导出和本地依赖管理 |

```bash
python tools/project.py doctor
python test/int8/run.py --count 32 --trained --soc
python tools/export_tiles.py --output tools/local/int8_tiles
python eda/remote.py run
```

本机功能测试使用 Icarus；完整 SoC 另需 ModelSim。当前训练权重读取与 tile 导出无需 NumPy；训练仍使用 model/requirements.txt。EDA 总控需要 Python 3.8+ 与 OpenSSH。大版图、授权库和中间数据库保留服务器；轻量结果回传 lab4 下新目录。

旧分支、旧 RTL 和旧范式记录保存在本地 archives，当前分支只保留更新后实现。第三方源码许可及固定输入来源见 [组件声明](report/THIRD_PARTY_NOTICES.md)。
