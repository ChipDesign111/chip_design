# HAR SoC

[![CI](https://github.com/ChipDesign111/chip_design/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ChipDesign111/chip_design/actions/workflows/ci.yml)

面向人体活动识别的 RISC-V SoC：CV32E40P + AXI + INT8 64→32→6 MLP NPU。当前交付为 RTL / SoC 功能仿真，FPGA 与 EDA 实现尚未开始。

| 目录 | 内容 |
| --- | --- |
| [rtl](rtl/README.md) | 完整 SoC 硬件：CPU、AXI、Debug、时钟/复位、存储、当前 NPU、统一源清单 |
| fpga | 空占位，后续 FPGA 实现 |
| [model](model/README.md) | MLP 训练、导出权重、量化规则和整数参考 |
| eda | 空占位，后续 EDA 工程 |
| [test](test/README.md) | 按日期组织测试脚本、testbench、输入、结果与报告 |
| [report](report/README.md) | 现行设计、接口和开发说明 |
| [tools](tools/README.md) | 工程入口、检查与下载工具；本地临时工具/受限资料 |

## 运行

Python 3.11+；RTL 使用 Icarus，模型验证另需 NumPy，完整 SoC 使用 ModelSim，结构检查使用 Yosys。

```sh
python -m pip install -r model/requirements.txt
python tools/project.py doctor
python tools/project.py check
python tools/project.py test --suite unit
python tools/project.py test --suite model
python tools/project.py test --suite memory
python tools/project.py test --suite model-soc --vsim /path/to/vsim
python tools/project.py synth
```

厂商 SRAM 功能仿真增加 `--memory ra1shd`，本地模型放入 tools/local/vendor；默认使用 portable-sram。详见 [开发说明](report/development.md) 和 [SRAM](report/sram.md)。每次测试在 `test/日期/runs/时间戳/` 保存脚本快照、结果、日志和报告。

当前 NPU 使用两个 FC1 tile、一个 FC2 tile，38 个同步权重 bank。单输入 39 周期，双输入 59 周期，重叠 18 周期。现有 MLP 全测试集历史整数准确率为 2504/2947（84.9678%）；硬件逐值一致性与模型分类准确率分别报告。

当前源码仅保留替换后的 HAR NPU，原 Lab3 NPU、4×4 回归与导入入口已删除。固定外围的 75 个保留文件沿用原字节校验；模型参数保持不变。来源和授权见 [组件声明](report/THIRD_PARTY_NOTICES.md)。

CPU 主 SRAM→NPU 装载支持独立 AXI burst DMA；协议和基准命令见 [DMA](report/dma.md)。

新增可选 [W8A4连续流水实现](report/streaming.md)：保持FC1 32×4、FC2 6×2和32路重定标，通过CHIP_STREAM_NPU启用连续调度、两帧DMA暂存及响应成功后提交。运行 `python tools/project.py test --suite stream-unit`；完整SoC基准使用 `--suite stream --vsim /path/to/vsim`。默认INT8路径继续保留；[实测报告](test/2026-10-20/stream/report.md)区分核心吞吐与整机加速。
