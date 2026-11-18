# 当前设计与验收

本目录只说明当前main。所有PPA和验收状态统一以[本版结果](results/README.md)及[机器可读记录](results/final_result.json)为准。

| 内容 | 入口 |
| --- | --- |
| SoC和计算通路 | [架构](architecture.md)、[NPU](npu.md)、[DMA](dma.md) |
| 软件/硬件接口 | [任务ABI](../compiler/TASK_ABI.md)、[兼容MMIO](mmio.md)、[兼容FC模式](fc_modes.md) |
| SRAM、启动和复位 | [存储协议](sram.md) |
| 复现功能验证 | [开发与验证](development.md) |
| 周期和流量 | [性能](performance.md) |
| 当前原始结果及对照 | [results](results/README.md) |
| 历史查阅 | [历史归档入口](history.md) |

results中的stage1是本轮冻结的旧路径对照，performance是最终实现的同网络/同输入结果；它们用于复现比较，不是两份待选硬件。optimized_functional保存本轮保护验证及7个带校验的后仿镜像。授权宏、版图数据库和完整本地构建不进入main。
