# ADR 0003: Exact integer inference contract

Status: Accepted

## Context

量化、舍入、符号扩展和 Argmax 平局规则会影响逐值结果。分类准确率与硬件计算正确性需要不同判定目标。

## Decision

INT8 输入/权重、INT32 合法累加；ReLU 后采用明确的整数乘数/移位、非负半入舍入和 0..127 饱和。第二层保留同尺度有符号得分，Argmax 平局取最小下标。累加溢出不属于合法输入，导出阶段检查范围。

模型精度对真实标签统计；RTL 和 CPU 结果对独立整数参考逐值比较。当前模型使用 MULT=1064、SHIFT=20，保持其原始参数和标签顺序。

## Consequences

语义变更必须联动模型导出、参考、RTL、固件和测试。合成边界和真实输入互补；模型误分类不应变成硬件测试失败。完整契约见 [numerics](../numerics.md)。
