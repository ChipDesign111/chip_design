# 人体活动识别 RISC-V SoC + NPU

ChipDesign111 的共有芯片设计项目。目标是在课程提供的 RISC-V SoC 基础上，实现运行 `64 → 32 → 6` 小型 MLP 的 INT8 NPU，完成算法参考、RTL、系统验证、FPGA 原型和 ASIC 交付。

**当前阶段：Lab 3 外围固定，HAR V1 已实现并完成 RTL/MMIO/真实 CPU 仿真。** 原四份 SoC 镜像通过；HAR 通过 1000 组核例、12 组 MMIO 和六次 CPU 连续推理。见 [验证报告](reports/baseline.md)。当前权重为合成测试数据，真实模型、FPGA 和 ASIC 待完成。

## 从这里开始

1. 阅读 [详细项目计划](docs/plan.md)，确认阶段顺序和验收点。
2. 阅读 [目录与硬件架构](docs/architecture.md)，确定各类文件放在哪里。
3. 阅读 [协作规范](CONTRIBUTING.md) 和 [环境说明](docs/environment.md)。
   开始改代码前，按 [修改与验证指南](docs/change-guide.md) 确认允许的修改区、编译入口和回归要求。
4. 评审 [V1 规格](docs/spec.md)、[数值规则](docs/numerics.md) 和 [MMIO](docs/mmio.md)。
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
python scripts/check_platform.py
python scripts/run_tests.py --unit
python scripts/run_tests.py --soc --vsim "本机 vsim 路径"
```

check_repo 检查结构与链接，check_platform 检查 90 个导入文件 SHA。--unit 使用 Icarus；--soc 使用 ModelSim，检查真实 CPU 写入的 PASS magic。工具安装及完整入口见 [环境说明](docs/environment.md)。两个 NPU 分开编译，都使用同一 Lab 3 外围。

## 课程来源与状态

- [课程主页](https://full-stack-ai-chip.tianyuj.com/)
- [Lab 3：SoC 集成与仿真](https://full-stack-ai-chip.tianyuj.com/lab-3/)
- [Final Project](https://full-stack-ai-chip.tianyuj.com/final-project/)
- 来源及发布时间核对见 [sources.md](docs/sources.md)。

2026-10-08 核对时，Lab 4–6 和 Final Project 尚未发布。人体活动识别方案依据课堂提供的场景 4；评分、分组和实现要求以最终公告为准。

## 共享边界

仓库公开。本次按用户要求选择性导入提供的 Lab 3 外围及原测试，保留来源、版权/许可证头和字节校验；未整包导入个人 Lab。未包含个人报告、真实数据集、PDK 或标准单元库。来源见 [平台说明](platform/course_soc/README.md)；课程材料后续使用范围以授权为准。
