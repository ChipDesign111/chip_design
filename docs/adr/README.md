# Architecture decision records

已接受的跨模块设计取舍采用 ADR 管理。变更应描述上下文、决策、影响和验证迁移；替代已有决策时保留旧记录并明确 superseded 状态。

| ADR | 状态 | 决策 |
| --- | --- | --- |
| [0001](0001-fixed-platform-boundary.md) | Accepted | 固定参考外围与可替换 NPU |
| [0002](0002-balanced-tiles.md) | Accepted | 异形 2:1 tile 与双输入两级流水 |
| [0003](0003-integer-contract.md) | Accepted | 精确整数契约与分类/计算质量分离 |
| [0004](0004-main-sram-backends.md) | Accepted | CPU 主 SRAM 编译覆盖、自有后端与本地宏依赖 |

早期非规范化决策记录位于 [archive](../archive/README.md)。
