# 团队硬件

[npu/](npu/README.md) 已实现 lab3 兼容核与 har MLP。主要修改 har/ 的计算和包装层；两份 simple_npu_top 分开编译。
[memory/](memory/README.md) 为存储拆分/适配预留；[soc/](soc/README.md) 暂无实现，系统顶层继续使用 platform 中固定的 Lab 3。当前 MMIO 和 NPU 本地存储位于 npu/har/simple_npu_top.sv。

改什么、如何新增编译源、如何跑回归，先看 [修改与验证指南](../docs/change-guide.md)。硬件层次见 [架构](../docs/architecture.md)。
