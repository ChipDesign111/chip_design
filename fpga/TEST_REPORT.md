# 当前FPGA验证状态

当前main的顺序任务NPU没有重新完成Vivado实现或上板验证。ASIC TT／课程EDA结果不能替代FPGA验证。

现有构建、时钟约束、JTAG装载和兼容专用固件保留，用作重新构建入口；本版必须从当前RTL重新生成bitstream，再验证时序、资源和模型输出。

已通过板测的旧版镜像与完整证据移至[历史归档](../report/history.md)。旧版PASS不作为当前main的板测结论。
