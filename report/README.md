# Design reports

这里保存现行设计与使用说明。功能测试记录按日期放在 [test](../test/README.md)；ASIC 流程的网表、SDF、数据库与完整日志放在忽略目录 `eda/work/`，精简验收摘要归 `test/日期/asic`。不在本目录重复存档。

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
| [ASIC 实现与验证 PPT](slides/HAR_SoC_ASIC_implementation_20261021.pptx) | 14 页课程汇报，含真实版图、面积、修复问题及四场景后仿结果 |

[DMA](dma.md)：AXI burst 装载、CSR、错误/并发规则与加速比测量；[验证记录](../test/2026-10-15/dma/report.md)。

[ASIC 综合和仿真](../eda/README.md)：完整 SoC 的课程工艺验证；[实测结果](../eda/RESULTS.md) 与 [JTAG 启动协议](../eda/BOOT_PROTOCOL.md)。
