# NPU 实现

外部端口采用固定 Lab 3 simple_npu_top；每次只编译一份：

- lab3/：4×4 无符号 4 位兼容核，用于原课程回归，保持不变。
- har/：HAR V2，2 个 16×4 FC1 tile、1 个 6×2 FC2 tile，banked 权重存储、两级计算流水和 hidden 双缓冲。

单样本 39 周期，双样本共 59 周期，两级实际重叠 18 周期。内部 core 接口已改为同步权重读口；外部 Lab 3 端口不变。旧单次 MMIO 窗口保留，双样本与性能寄存器见 [MMIO](../../docs/mmio.md)。

架构/代码/时序见 [tiled-npu.md](../../docs/tiled-npu.md)，数值见 [numerics.md](../../docs/numerics.md)，证据见 [V2 报告](../../reports/tiled-v2.md)。V1 报告是历史版本，不代表当前代码。未验证目标 PPA、FPGA 或 ASIC。
