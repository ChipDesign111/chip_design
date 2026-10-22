# HAR SoC

[![CI](https://github.com/ChipDesign111/chip_design/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ChipDesign111/chip_design/actions/workflows/ci.yml)

面向人体活动识别的 RISC-V SoC：CV32E40P + AXI + INT8 64→32→6 MLP NPU。已完成 RTL / SoC 功能验证、完整 SoC 的 ASIC 综合与综合前后仿，以及 Innovus 布局布线、静态物理检查和约束覆盖分类。布线后 SDF 已按明确的外部上电协议完成 MAX/MIN 四场景验收，FPGA 尚未实现。

| 目录 | 内容 |
| --- | --- |
| [rtl](rtl/README.md) | 完整 SoC 硬件：CPU、AXI、Debug、时钟/复位、存储、当前 NPU、统一源清单 |
| fpga | 空占位，后续 FPGA 实现 |
| [model](model/README.md) | MLP 训练、导出权重、量化规则和整数参考 |
| [eda](eda/README.md) | TSMC180 Genus 综合、Innovus 布局布线、Xcelium 前后仿及独立证据核查 |
| [test](test/README.md) | 按日期组织测试脚本、testbench、输入、结果与报告 |
| [report](report/README.md) | 现行设计、接口和开发说明 |
| [tools](tools/README.md) | 工程入口、检查与下载工具；本地临时工具/受限资料 |

## 运行

Python 3.11+；RTL 使用 Icarus，模型验证另需 NumPy，完整 SoC 使用 ModelSim，结构检查使用 Yosys。

课程服务器上的工艺综合和前后仿使用 Genus/Xcelium，独立入口支持 Python 3.8+，见 [EDA](eda/README.md)。

本轮[14 页汇报 PPT](report/slides/HAR_SoC_ASIC_implementation_20261021.pptx) 包含综合、CTS、布线及后仿结果；[真实版图预览](test/2026-10-21/pnr/figures/README.md) 保存 CTS 后与最终布线后的 DEF/LEF 几何渲染。

当前完整 SoC 已完成 3400.32 μm 见方 Die 的 route / finish / export：TT 下最终 setup 裕量 +1.217 ns、hold +0.018 ns，TNS、违反端点和 DRV 均为 0，独立物理审计 8 项及约束覆盖分类通过。原 MAX 基线有 3 条上电时序违规，不能计为动态 PASS；在“复位有效、外部系统时钟先保持低 1000 ns”的协议下，MAX/MIN 四个完整场景均已实际 **PASS**，每场景完成两次启动、2048 字下载及回读，时序诊断为 0。范围与启动条件见 [物理实现结果](eda/pnr/RESULTS.md) 和 [启动协议](eda/BOOT_PROTOCOL.md)，尚非全 PVT 或 foundry 签核。

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

当前源码仅保留替换后的 HAR NPU，原 Lab3 NPU、4×4 回归与导入入口已删除。本轮相对 GitHub `52be8c5` 修改两个 RTL 文件：bootram 默认首指令等待 JTAG 装载，SoC 顶层在原四级同步器后增加下降沿复位释放寄存器，见 [启动协议](eda/BOOT_PROTOCOL.md)。模型参数保持不变。

外围清单检查 75 个文件的当前 SHA，其中累计 3 个文件有记录的项目集成修改，72 个文件保持课程原字节；原始哈希和修改历史以 `rtl/manifest.json` 为准。保留的 `rtl/README.md` 和 `rtl/soc/README.md` 是原导入说明，其中“原字节”描述不覆盖这些后续修改。来源和授权见 [组件声明](report/THIRD_PARTY_NOTICES.md)。

CPU 主 SRAM→NPU 装载支持独立 AXI burst DMA；协议和基准命令见 [DMA](report/dma.md)。
