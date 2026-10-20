# SoC 集成入口

| 文件 | 职责 |
| --- | --- |
| [my_soc_top.sv](my_soc_top.sv) | CV32E40P、Debug、DMA、AXI、Boot、主SRAM和NPU接线 |
| [my_npu_subsystem.sv](my_npu_subsystem.sv) | NPU窗口、DMA CSR、访问来源标记/忙时保护、NPU配置选择 |

CPU、Debug与DMA共享AXI。CPU取指/数据和DMA源读取也共享主SRAM，因而供数受总线仲裁影响；NPU的本地权重bank不占主SRAM的计算读带宽。

定义 `CHIP_STREAM_NPU` 时选择 `har_stream_top` 与 `har_stream_dma`，默认选择INT8兼容实现。模块定义都由 [统一清单](../filelist.f) 提供，不能靠删除baseline文件切换配置。

两个集成文件已在 [manifest](../manifest.json) 记录项目接入修改。改端口、地址或访问规则时同步清单/配置和文档，运行 `check`、最终版 `stream` 及兼容版 `model-soc`。日常算术优化从 [npu](../npu/README.md) 开始；外围源码集中于 [platform](../platform/README.md)。
