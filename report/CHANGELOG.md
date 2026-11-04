# 当前架构变更

2026-11-04：修复后仿固件用例范围。后仿原先错误请求训练 seed `10000..10011`，但当前 `har_uci24.json` 只包含 24 条输入，只能组成 `10000..10005` 六组四样本；从 seed `10006` 起输入为空却仍按 batch=4 运行，导致 CPU 自检失败。后仿现改为六组训练加四组随机，并在样本不足时拒绝生成固件。

2026-11-03：内部 FC1/FC2 累加、Argmax 比较和重定标输入从 signed 32 位收窄为 signed 22 位。32 位 MMIO bias 仅解释低 22 位符号数，32 位 score 窗口由 INT22 内部值符号扩展；重定标乘法改为 22×16，中间积收窄为 38 位。随机测试改用 INT22 补码回绕，边界 bias 改为 `-2^21` 与 `2^21-1`。同源 34 步 EDA 完成：全 SoC Cell Area 2.062446 mm²，NPU 0.896961 mm²，含 PAD Die 3.795639 mm²；20 ns 下 Setup/Hold WNS 为 +0.032/+0.019 ns，关键路径转移到 CPU ALU。SDF 后仿和独立 foundry DRC/LVS 仍待执行。

2026-11-03：三级重定标流水后的综合表明 QUANT 路径已退出最差路径列表；剩余关键路径为 CPU IF/ID → AXI Crossbar AR 通道 → AXI2NPU → NPU 地址和读数据选择，slack 仅 +0.8 ps。AXI crossbar 从 `NO_LATENCY` 改为 `CUT_SLV_AX`，只寄存 slave 端 AW/AR 地址通道。功能和 ModelSim 回归通过，完整 SoC 总周期从 5121 增至 6337 拍；综合、实现和 SDF 仍需重跑。

2026-11-03：根据 preCTS 路径把 FC2 从每拍 4 输入行改为每拍 2 输入行，并将单周期六路 Argmax 改为共享 32 位比较器的逐拍扫描。修改目标是在保留 batch=1/2/4 接口的同时缩短 `tile_index → FC2 动态选择 → 乘法累加` 路径并降低比较树面积。用户本地 38/38 单元用例、训练模型和完整 SoC 回归通过；batch=1/2/4 NPU 为 1401/1431/1541 拍，完整 SoC 为 6369 拍。综合和物理验证待独立重跑。

2026-11-03：根据 Placement 路径报告纠正时序修改方向。最差路径实际为 `quant_sample_reg → a1[sample][output] 动态选择 → requant_multiplier → h_reg`，不是 MAC 乘加路径。撤销增加 512 bit 乘积寄存器的 MAC 流水，改为 sample/8 输出组选择、8 选 1、32×16 乘法饱和三级重定标流水；每拍仍处理一个输出，FC1 末尾增加两拍排空。38/38 单元用例、训练模型、Boot 起点、冷启动 Debug 和完整 SoC ModelSim 全部通过；batch=1/2/4 NPU 为 1395/1415/1514 拍，完整 SoC testbench/硬件周期为 5121/5116 拍，DMA 读/写重叠为 269/268。综合、物理实现和 SDF 仍需重跑。

2026-11-03：为 20 ns ASIC 时序加入共享 32-MAC 乘积流水。ISSUE 周期寄存 512 bit 乘积，下一周期完成 lane 求和和 INT32 累加，层末各增加一个排空周期；下一组乘积仍可逐拍发射。38/38 单元用例、训练模型、Boot 起点、冷启动 Debug 和完整 SoC ModelSim 全部通过。batch=4 NPU 从 1512 增至 1515 拍，完整 SoC testbench/硬件周期从 5109/5104 增至 5121/5116 拍；DMA 读/写重叠变为 268/267。综合、物理实现和 SDF 仍需重跑。

2026-11-01：最终无预装载 `impl_2` 在 20 MHz 通过 routed timing，WNS/WHS 为 +0.368/+0.017 ns，LUT 19,459。T08 板上完成：PASS、最终 PC 正确、Boot word14 为 `0x000013F1`（5105 拍）；bitstream SHA-256 为 `e4247f4a...24c917b6`。

2026-11-01：T08 周期计数器改为在 `soc_cycles` 上原地冻结，删除冗余的 32-bit `soc_cycles_final` 及其加法/回读选择逻辑。Boot 起点单测、38 个单元用例和完整 SoC 通过，硬件口径保持 5104 拍；资源与时序需重新综合实现。

2026-11-01：取消 Boot 地址限定后的板上版本仍将 debug mode 内部取指计入，读到 `0x069777BC`；RTL 接入 CV32E40P `debug_halted_o`，只在 `boot_ready` 后首次非 debug CPU 取指时启动。38 个单元用例和完整 SoC 通过，硬件口径仍为 5104 拍，板上读取待新 bitstream。

2026-11-01：板上 Boot 地址限定版本在 PASS 和最终 PC 正确时仍读到 0，确认 OpenOCD 可能从保存的 DPC 直接恢复而不再次取指 Boot 跳板。RTL 改为 `boot_ready` 后第一次任意 CPU 取指触发；38 个单元用例和完整 SoC 再次通过，硬件周期仍为 5104 拍，板上读取待新 bitstream。

2026-11-01：完整 SoC 周期计数改为在 `boot_ready` 后首次从 `0x00010000` 取指时启动，排除镜像装载、commit、debug halt 和 JTAG resume 延迟。新增 Boot 周期起点单测；38 个单元用例和完整 SoC 通过，testbench 观测 5109 拍，新硬件口径为 5104 拍，板上读取待新 bitstream。

2026-10-31：完成 T09，将当前 FPGA 文档、RTL 工程元数据和源码注释统一为 20 MHz，并在根目录及 FPGA 入口补充板级测试报告索引。历史 25/50 MHz 条目保留，用于区分旧配置与当前 XCI/routed timing 证据。

2026-10-30：将共享 MAC bank 从 64 减为 32。FC1 分两个 16 输出相位，FC2 分两个 4 输入行相位，64 B bank 和 48 B W2 包保持不变。固定基准 batch=1/2/4 NPU 为 1395/1413/1512 拍，相比 64-MAC 仅增加 1/3/9 拍；完整 SoC batch=4 从 5101 增至 5109 拍。综合、实现和时序仍待重跑。

2026-10-30：从 `43f5e38` 移植共享 SRAM 事务复位边界到 `rtl-dev`，保留共享 64 MAC、batch=4 和 25 MHz `NO_LATENCY` 配置。SRAM AXI 桥与 `my_mainmem` 使用同一个下降沿限定复位，仅 SRAM 桥启用 `QUIET_ON_RESET`。功能回归通过，综合、实现和对应物理/SDF 证据待重跑。

2026-10-30：将 FC1/FC2 改为共享 64 个 INT8 乘法器。FC1 保持 32 输出×2 lane；FC2 使用同一 bank 映射为 6 输出×8 输入行，物理权重包仍为 48 B，FC2 发射周期从 `batch×32` 降为 `batch×4`。固定基准 batch=1/2/4 NPU 为 1394/1410/1503 拍，完整 SoC batch=4 为 5101 拍。对应物理实现和 25 MHz 时序尚未重跑。

2026-10-30：FPGA 选择 25 MHz 系统时钟，AXI crossbar 从 `CUT_SLV_AX` 恢复为 `NO_LATENCY`。功能与完整 SoC 回归通过，batch=4 完整 SoC 从 6403 拍降至 5193 拍。该时钟和时序结论仅适用于 FPGA，不改变 50 MHz ASIC 目标证据。

2026-10-29：batch=4 综合仍超出少量 LUT。权重 bank 显式映射为寄存器以释放 distributed RAM 占用的 LUT 站点；各样本 Argmax 合并为一个共享单元，在 FINISH 中依次完成。batch=4 NPU 增加 7 拍，完整 SoC 保持 6403 拍。

2026-10-29：为控制 A7-35T LUT 占用，最大 batch 从 8 降为 4。样本 4..7 的输入、累加器、hidden、scores 和 class 寄存器被移除，保留的 MMIO 槽输出为零；随机与训练回归调整为 batch=1/2/4，FPGA 自检镜像同步重生成。

2026-10-29：撤销乘加流水；AXI 交叉开关从 `NO_LATENCY` 改为 `CUT_SLV_AX`，在 slave 端 demux 的 AW/AR 地址通道增加寄存器边界，以切断导致 FPGA 42 级逻辑的跨模块控制路径，同时避免 W/R 数据通道和 master mux 增加额外延迟。

2026-10-28：支持最多八样本寄存器批次；tile 最后一个样本发射时立即释放，下一 bank 已就绪则零气泡交接。FC2 每 8 个逻辑 tile 打包为 48B，W2 共 4 次 DMA，并在 W1 尾部与 requant 期间提前预取。固定基准 batch=8 从 2025 拍降至 1808 拍。物理 PPA 尚未重签。

2026-10-23：从 main 267c873 重建 xzx；改为 INT8 2×32 / 1×6、两份 64B tile 缓冲、共享重定标和流式 DMA；完整权重放主 SRAM，按 tile 复用当前批全部样本。加入完整镜像覆盖、显式启动提交和复位同步余量。部署仍按单次上传隔离，三个阶段分别运行，面积按含 PAD 的整个 Die 验收。
