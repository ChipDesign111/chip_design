# ADR 0002: Balanced tiled pipeline

Status: Accepted

## Context

两层工作量为 2048 和 192 MAC，相同 tile 配成 2:1 仍无法均衡层耗时。层间依赖也意味着单输入的两层不能直接同时执行。

## Decision

FC1 使用两个 16-output/4-lane tile，FC2 使用一个 6-output/2-lane tile；各发射 16 个分块。产品寄存器、累加和 hidden 双缓冲支持不同输入间的两级重叠。批长度限定为 1 或 2，参数共享。

## Consequences

两级每输入各活跃 19 周期，单 / 双输入为 39 / 59 周期，双模式重叠 18 周期。tile 数量比 2:1 不代表乘法器或面积比 2:1；点积乘法器为 128:12，另有 32 个量化乘法器。目标存储映射与物理成本仍需验证。详见 [tiled-npu](../tiled-npu.md)。
