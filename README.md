# HAR SoC

[![CI](https://github.com/ChipDesign111/chip_design/actions/workflows/ci.yml/badge.svg?branch=xzx%2Frtl)](https://github.com/ChipDesign111/chip_design/actions/workflows/ci.yml)

人体活动识别SoC：CV32E40P + AXI + 64→32→6 MLP NPU。当前开发分支 `xzx/rtl` 使用可选W8A4连续流水配置；未定义 `CHIP_STREAM_NPU` 时仍构建INT8兼容路径。当前交付是RTL/完整SoC功能仿真。

| 目录 | 入口与职责 |
| --- | --- |
| [rtl](rtl/README.md) | 四块硬件：soc集成 / platform外围 / npu计算 / dma搬运；含阅读顺序、修改范围及验证方法 |
| [model](model/README.md) | 权重、特征、量化配置、整数参考与模型质量 |
| [test](test/README.md) | 测试脚本、输入、结果和按日期归档的证据 |
| [report](report/README.md) | 架构、接口、设计与开发说明 |
| [tools](tools/README.md) | 统一工程入口和检查；受限资料只存忽略的tools/local |
| fpga / eda | FPGA与后端实现工程，当前为空占位 |

## 从这里开始

先读 [RTL目录说明](rtl/README.md)，再读 [最终流水设计](report/streaming.md)。Python需要3.11+与NumPy，核级用Icarus，完整SoC用ModelSim，通用结构检查用Yosys。

```sh
python -m pip install -r model/requirements.txt
python tools/project.py check
python tools/project.py test --suite stream-unit
python tools/project.py test --suite stream --vsim /path/to/vsim
python test/2026-10-20/scripts/check_stream_synthesis.py --yosys /path/to/yosys
```

全2947条输入验证加 `--data-root "model/data/UCI HAR Dataset"`；有授权SRAM模型时SoC测试加 `--memory ra1shd`，否则默认portable-sram。INT8兼容回归使用 `unit`、`model`、`model-soc` 及 `synth`；全部命令见 [开发说明](report/development.md)。运行日志、向量、源SHA和脚本快照只生成到忽略的 `test/日期/runs/`。

## 已验证的结果

FC1为32×4路、FC2为6×2路，另有32路重定标乘法，权重常驻38个bank共2240 B。24条真实输入的完整版本比较：整机13619→4972周期（2.739×），装载权重后11404→3314周期（3.441×）。两版CPU类别收集与校验工作量一致；完整口径和双SRAM证据见 [性能报告](test/2026-10-20/version-compare/report.md)。

W8A4全测试集准确率2490/2947（84.4927%），原INT8为2504/2947（84.9678%）。实现逐值一致性与分类准确率分别报告；原checkpoint曾用该测试集选优，非独立盲测。无FPGA实测或目标工艺PPA签核结论。来源、版权与授权见 [组件声明](report/THIRD_PARTY_NOTICES.md)。
