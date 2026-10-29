# 当前架构变更

2026-10-30：将 FC1/FC2 改为共享 64 个 INT8 乘法器。FC1 保持 32 输出×2 lane；FC2 使用同一 bank 映射为 6 输出×8 输入行，物理权重包仍为 48 B，FC2 发射周期从 `batch×32` 降为 `batch×4`。固定基准 batch=1/2/4 NPU 为 1394/1410/1503 拍，完整 SoC batch=4 为 5101 拍。对应物理实现和 25 MHz 时序尚未重跑。

2026-10-30：FPGA 选择 25 MHz 系统时钟，AXI crossbar 从 `CUT_SLV_AX` 恢复为 `NO_LATENCY`。功能与完整 SoC 回归通过，batch=4 完整 SoC 从 6403 拍降至 5193 拍。该时钟和时序结论仅适用于 FPGA，不改变 50 MHz ASIC 目标证据。

2026-10-29：batch=4 综合仍超出少量 LUT。权重 bank 显式映射为寄存器以释放 distributed RAM 占用的 LUT 站点；各样本 Argmax 合并为一个共享单元，在 FINISH 中依次完成。batch=4 NPU 增加 7 拍，完整 SoC 保持 6403 拍。

2026-10-29：为控制 A7-35T LUT 占用，最大 batch 从 8 降为 4。样本 4..7 的输入、累加器、hidden、scores 和 class 寄存器被移除，保留的 MMIO 槽输出为零；随机与训练回归调整为 batch=1/2/4，FPGA 自检镜像同步重生成。

2026-10-29：撤销乘加流水；AXI 交叉开关从 `NO_LATENCY` 改为 `CUT_SLV_AX`，在 slave 端 demux 的 AW/AR 地址通道增加寄存器边界，以切断导致 FPGA 42 级逻辑的跨模块控制路径，同时避免 W/R 数据通道和 master mux 增加额外延迟。

2026-10-28：支持最多八样本寄存器批次；tile 最后一个样本发射时立即释放，下一 bank 已就绪则零气泡交接。FC2 每 8 个逻辑 tile 打包为 48B，W2 共 4 次 DMA，并在 W1 尾部与 requant 期间提前预取。固定基准 batch=8 从 2025 拍降至 1808 拍。物理 PPA 尚未重签。

2026-10-23：从 main 267c873 重建 xzx；改为 INT8 2×32 / 1×6、两份 64B tile 缓冲、共享重定标和流式 DMA；完整权重放主 SRAM，按 tile 复用当前批全部样本。加入完整镜像覆盖、显式启动提交和复位同步余量。部署仍按单次上传隔离，三个阶段分别运行，面积按含 PAD 的整个 Die 验收。
