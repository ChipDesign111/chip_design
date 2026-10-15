# HAR-NPU

[![CI](https://github.com/ChipDesign111/chip_design/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ChipDesign111/chip_design/actions/workflows/ci.yml)

**面向人体活动识别的 INT8 tiled 加速器与 RISC-V SoC 参考实现。**

HAR-NPU 实现固定 `64 → 32 → 6` MLP，集成 CV32E40P、AXI 和 MMIO 控制接口。工程覆盖整数参考模型、可综合 RTL、同步权重存储、裸机自检程序及分层验证。

当前交付状态为 **RTL / SoC 仿真验证完成**。FPGA 适配、目标工艺综合、时序与物理签核不属于已验证能力。

## 核心能力

| 项目 | 实现 |
| --- | --- |
| 计算 | INT8 输入/权重，INT32 偏置/累加/得分 |
| 网络 | 2,278 个参数，2,240 MAC / 输入；ReLU、整数重新量化、Argmax |
| 并行结构 | FC1：2×16-output/4-lane tile；FC2：1×6-output/2-lane tile |
| 存储 | 38 个同步权重 bank，2,240 B 权重容量，hidden 双缓冲 |
| 调度 | 单输入或双输入批次；跨输入的两级流水重叠 |
| 控制 | 32-bit MMIO，状态/错误/周期计数，运行中写保护 |
| 集成 | 固定参考外围；独立 `lab3` 兼容与 `har` 编译配置 |

单输入核心延迟 **39 周期**；双输入批次 **59 周期**，两级重叠 **18 周期**。这些是 RTL 仿真周期，不代表已达到的芯片频率或功耗。

## 快速开始

需要 Python 3.11+、Icarus Verilog；模型验证使用锁定的 NumPy 版本。

```sh
python -m pip install -r requirements.txt
python project.py doctor
python project.py check
python project.py test --suite unit
python project.py test --suite model
python project.py test --suite memory
```

通用综合结构检查与完整 SoC 仿真：

```sh
python project.py synth --yosys /path/to/yosys
python project.py test --suite soc --vsim /path/to/vsim
python project.py test --suite model-soc --vsim /path/to/vsim
```

可执行文件已在 PATH 时省略路径参数。Windows 路径带空格时使用引号。完整依赖、环境诊断和常见问题见 [环境配置](docs/environment.md)。

## 验证基线

以下结果对应已记录的仿真基线，详细命令、输入 SHA 和适用范围见 [验证报告](reports/README.md)。

| 验证范围 | 结果 |
| --- | --- |
| 合成参数边界回归 | 1,000 组、3,000 次推理，逐值一致 |
| 真实 UCI HAR 测试数据 | 2,947 条、单/双模式共 5,894 次推理，逐值一致 |
| 完整 CPU / SoC | 原平台四镜像、加速器自检、六类 24 条真实输入通过 |
| 整数模型识别准确率 | 2,504 / 2,947，84.9678% |
| 平台完整性 | 90 个冻结文件 SHA-256 一致 |
| 通用综合结构 | 38 个 RAM、76 个同步读端口、无锁存器 |

模型准确率衡量分类质量；RTL 与整数参考一致性衡量硬件计算正确性，两者分别报告。

## 工程导航

| 路径 | 职责 |
| --- | --- |
| [rtl/](rtl/README.md) | 加速器 RTL 与存储/流水调度 |
| [platform/](platform/README.md) | 固定参考 SoC 与来源清单 |
| [model/](model/README.md) | 训练产物、量化参数、整数参考 |
| [verification/](verification/README.md) | 核级、MMIO、原平台及真实模型验证 |
| [sw/](sw/README.md) | 启动材料与裸机自检生成 |
| [scripts/](scripts/README.md) | 编译、仿真、导出与结构检查后端 |
| [configs/](configs/README.md) | 机器可读规格 |
| [docs/](docs/README.md) | 架构、接口、开发和发布规范 |
| [reports/](reports/README.md) | 版本化验证证据 |

- [架构](docs/architecture.md) · [功能规格](docs/spec.md) · [MMIO](docs/mmio.md) · [整数契约](docs/numerics.md)
- [验证策略](docs/verification.md) · [修改指南](docs/change-guide.md) · [真实模型验证](docs/model-verification.md)
- [贡献规范](CONTRIBUTING.md) · [变更记录](CHANGELOG.md) · [发布流程](docs/releases.md) · [路线图](docs/roadmap.md)

第三方组件及数据按各自来源条款管理，见 [组件声明](THIRD_PARTY_NOTICES.md)。版权/许可证头、原测试和来源校验属于工程基线。

CPU 主存支持可选 2048×32 单端口 SRAM 适配，见 [SRAM 接入](docs/sram.md)。厂商视图为本地依赖，公开 CI 使用自有行为后端。
