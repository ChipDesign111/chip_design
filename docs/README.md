# Engineering documentation

## 使用与集成

| 文档 | 内容 |
| --- | --- |
| [environment.md](environment.md) | 工具依赖、统一命令、诊断与构建产物 |
| [spec.md](spec.md) | 功能范围、能力状态和兼容边界 |
| [architecture.md](architecture.md) | SoC 层次、实现归属和构建配置 |
| [mmio.md](mmio.md) | 寄存器、地址窗口、握手和错误语义 |
| [numerics.md](numerics.md) | 位宽、舍入、饱和和 Argmax 契约 |
| [tiled-npu.md](tiled-npu.md) | tile 配比、存储与两级流水时序 |
| [memory-budget.md](memory-budget.md) | 主存与加速器本地数据预算 |

## 开发与验证

| 文档 | 内容 |
| --- | --- |
| [change-guide.md](change-guide.md) | 修改边界、编译入口和最低回归要求 |
| [verification.md](verification.md) | 验证层次、通过条件与 CI 覆盖 |
| [model-verification.md](model-verification.md) | 已选模型和真实输入的验证路径 |
| [adr/](adr/README.md) | 已接受的架构决策 |
| [releases.md](releases.md) | 发布候选、版本与证据清单 |
| [roadmap.md](roadmap.md) | 能力缺口、交付条件与优先级 |
| [provenance.md](provenance.md) | 组件来源与基线更新规则 |

[贡献规范](../CONTRIBUTING.md)、[验证报告](../reports/README.md)、[组件声明](../THIRD_PARTY_NOTICES.md) 是配套入口。
[历史归档](archive/README.md) 保存早期规划和开发记录，不作为现行工程规范。
