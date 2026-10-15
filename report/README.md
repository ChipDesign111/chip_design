# Design reports

这里保存现行设计与使用说明。每次测试的结果、日志和报告统一放在 [test](../test/README.md)，不在这里重复存档。

| 文档 | 内容 |
| --- | --- |
| [architecture.md](architecture.md) | 完整 SoC、目录边界、存储与修改范围 |
| [npu.md](npu.md) | tile 配比、两级流水、bank 存储和周期 |
| [mmio.md](mmio.md) | 寄存器、数据布局和协议 |
| [sram.md](sram.md) | SRAM 后端、本地资料和仿真边界 |
| [development.md](development.md) | 工具依赖、修改方法、验证与交付 |
| [整数规则](../model/numerics.md) | MLP 数值契约 |
| [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) | 组件来源与授权 |
| [CHANGELOG.md](CHANGELOG.md) | 工程变更 |

[DMA](dma.md)：AXI burst 装载、CSR、错误/并发规则与加速比测量；[验证记录](../test/2026-10-15/dma/report.md)。
