# HAR W8A4 SoC

[![CI](https://github.com/ChipDesign111/chip_design/actions/workflows/ci.yml/badge.svg?branch=xzx%2Frtl)](https://github.com/ChipDesign111/chip_design/actions/workflows/ci.yml)

`xzx/rtl` 只维护最终版：CV32E40P + AXI + W8A4 64→32→6 MLP NPU，配套流式DMA、片上权重bank和两级连续流水。默认构建即为此设计，无需选择宏。

| 目录 | 内容 |
| --- | --- |
| [rtl](rtl/README.md) | soc集成、platform外围、npu计算、dma搬运 |
| [model](model/README.md) | 唯一部署权重、量化参数和整数参考 |
| [test](test/README.md) | 最终版核级、DMA、SRAM及完整SoC验证 |
| [report](report/README.md) | 最终版架构、接口、设计与验证方法 |
| [tools](tools/README.md) | 统一入口、RV32I固件生成及检查 |
| fpga / eda | 后续实现占位 |

```sh
python -m pip install -r model/requirements.txt
python tools/project.py check
python tools/project.py test --suite unit
python tools/project.py test --suite soc --vsim /path/to/vsim
python tools/project.py synth --yosys /path/to/yosys
```

全2947条输入：`test --suite unit --data-root "model/data/UCI HAR Dataset"`。授权主SRAM模型测试增加 `--memory ra1shd`。运行产物在忽略的 `test/日期/runs/`。阅读 [RTL说明](rtl/README.md) 后开始修改。

旧INT8实现、旧驱动/测试/训练材料及版本比较程序保存在仓库外的本地归档，含完整源码、Git bundle和SHA清单。管理方法见 [归档说明](report/local_archive.md)。当前分支不依赖本地归档或旧Git历史即可构建和测试。

当前仅交付功能仿真与通用结构检查，FPGA和目标工艺签核尚未完成。来源与授权见 [组件声明](report/THIRD_PARTY_NOTICES.md)。
