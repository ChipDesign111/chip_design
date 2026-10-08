# NPU 计算核

外部端口沿用 Lab 3 simple_npu_top。每次只编译一份：

- lab3/：本次实现的 4×4 无符号 4 位兼容核，原课程回归。
- har/：一个 MAC 的 INT8 两层 64→32→6 MLP，偏置、ReLU、重新量化、Argmax。

HAR 每次计算 2279 周期，参数与输入由 MMIO 装载。见 [数值](../../docs/numerics.md)、[MMIO](../../docs/mmio.md) 和 [报告](../../reports/baseline.md)。尚无 PPA 或上板证据。
