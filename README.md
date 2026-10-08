# 人体活动识别 RISC-V SoC + NPU

ChipDesign111 的共有芯片设计项目。目标是在课程提供的 RISC-V SoC 基础上，实现运行 `64 → 32 → 6` 小型 MLP 的 INT8 NPU，完成算法参考、RTL、系统验证、FPGA 原型和 ASIC 交付。

**当前阶段：共有仓库架构与计划已建立，功能实现尚未开始。** 本仓库独立于各成员的个人 Lab；个人成果通过任务分支、验证和 PR 进入共有项目。

## 从这里开始

1. 阅读 [详细项目计划](docs/plan.md)，确认阶段顺序和验收点。
2. 阅读 [目录与硬件架构](docs/architecture.md)，确定各类文件放在哪里。
3. 阅读 [协作规范](CONTRIBUTING.md) 和 [环境说明](docs/environment.md)。
4. 评审 [规格草案](docs/spec.md)、[数值规则草案](docs/numerics.md) 和 [MMIO 草案](docs/mmio.md)。
5. 从 [任务清单](docs/backlog.md) 领取任务；当前不预先安排四人分工。

## 项目规模

| 项目 | 数量 |
| --- | ---: |
| 第一层权重 / 偏置 | 2,048 / 32 |
| 第二层权重 / 偏置 | 192 / 6 |
| 参数总数 | 2,278 |
| 每条输入的乘加数 | 2,240 |
| 输入 | 64 维 INT8 特征 |
| 输出 | 六个整数得分与类别编号 |

活动类别为步行、上楼、下楼、站立、坐、躺卧。编号映射需与真实数据集确认，见规格草案。

## 共有目录

| 目录 | 内容 |
| --- | --- |
| [platform/](platform/README.md) | 共同选择的官方平台源码及其来源记录 |
| [rtl/](rtl/README.md) | 团队开发的 NPU、存储适配和 SoC 集成 |
| [model/](model/README.md) | 训练、量化、整数参考与数据导出 |
| [sw/](sw/README.md) | CPU 驱动、裸机测试和启动配置 |
| [verification/](verification/README.md) | 单元、NPU、MMIO、SoC 测试与固定向量 |
| [filelists/](filelists/README.md) | 明确每种仿真的编译源文件 |
| [scripts/](scripts/README.md) | 共有运行、构建与检查入口 |
| [configs/](configs/README.md) | 项目配置与本地配置示例 |
| [fpga/](fpga/README.md) | 板级适配与 FPGA 约束 |
| [asic/](asic/README.md) | 综合、后端、签核的配置与入口 |
| [reports/](reports/README.md) | 共有版本的验证和实现结果摘要 |
| [docs/](docs/README.md) | 规格、计划、接口、记录 |

目录 README 表示开发边界，不表示该模块已经实现。构建产物写入被忽略的 `build/`。

## 当前能运行的检查

需要 Python 3.11 或更新版本；从仓库根目录执行：

```text
python scripts/check_repo.py
```

该命令检查目录、文档链接、基础配置和 MMIO 窗口布局。它不运行模型、RTL、SoC 或 EDA。后续功能入口随对应任务增加。

## 课程来源与状态

- [课程主页](https://full-stack-ai-chip.tianyuj.com/)
- [Lab 3：SoC 集成与仿真](https://full-stack-ai-chip.tianyuj.com/lab-3/)
- [Final Project](https://full-stack-ai-chip.tianyuj.com/final-project/)
- 来源及发布时间核对见 [sources.md](docs/sources.md)。

2026-10-08 核对时，Lab 4–6 和 Final Project 尚未发布。人体活动识别方案依据课堂提供的场景 4；评分、分组和实现要求以最终公告为准。

## 共享边界

仓库目前公开。初始版本只包含团队规划、原创说明及仓库工具，未导入课程原包、个人实验报告、数据集或 PDK。后续引入代码须确认共享范围、保留来源和许可证；公开性不能替代课程授权。详见 [协作规范](CONTRIBUTING.md)。
