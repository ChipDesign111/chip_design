# 完整 SoC 工艺综合与仿真结果

2026-10-20 至 21 日以 GitHub `52be8c57b365b70536500526a52905352e505666` 为基线，对完整 CPU、AXI、DMA 和 HAR NPU 建立 TSMC180 ASIC 验证流程。实际运行目录为课程服务器 `$PROJECT_ROOT`，本地分支为 `codex/asic-synthesis-20261020`。门级和 SDF 分别暴露启动及复位释放问题，现修改 bootram 默认首指令，并在 SoC 顶层增加下降沿复位释放寄存器，来源清单同步保留原哈希，见 [启动与复位协议](BOOT_PROTOCOL.md)。

本轮修改后工作树的运行标签为 `52be8c57b365b70536500526a52905352e505666+bootwait-resetfall-working-tree`，实验时以工作树逐文件哈希固定，不把该运行标签当作新的 Git 提交。92 个 RTL/包含文件/来源元数据以逐文件哈希固定；外围清单的 75 项当前 SHA 检查包括累计 3 个有记录的项目 override，72 个保持课程原字节。

## 当前验收

| 阶段 | 结果 | 实际证据 |
| --- | --- | --- |
| RTL 引脚级前仿 | PASS | `eda/work/asic-resetfall/rtl`：synthetic、dma 各两次启动；损坏下载负例被拒绝 |
| TSMC180 工艺综合 | PASS：最终版本完整重新综合、正常退出 | `eda/work/asic-resetfall/synthesis`；无 Error/Fatal |
| 门级功能后仿 | PASS：最终版本两套完整自检，各两次启动 | `eda/work/asic-resetfall/gate`；采用官方零延迟 UDP NBA 选项 |
| 综合后 SDF 时序后仿 | PASS：synthetic、dma 各两次启动，无时序违规 | `eda/work/asic-resetfall/sdf`；旧版本的 445 条 removal 违规保留为失败记录 |
| 独立时钟/CDC 约束审计 | PASS | `eda/work/clock-coverage-resetfall` |
| 跨阶段哈希和原始日志审计 | PASS | `verification.json`、`verification-final.json`；后者另核对冻结源码快照 |

测试通过条件是通过顶层 JTAG 写入并回读全部 2048 个程序字，CPU 实际执行自检并写入 `c0dec0de`。每个正例先清除旧完成标志，再做两次复位启动。测试台不初始化或强制 DUT 内部节点。

`synthetic` 覆盖 39/59/18 周期和量化边界；`dma` 覆盖 24 个真实样本的 hidden、score、class 与 DMA 完成状态。RTL 另故意损坏第 7 个下载字，必须在回读时拒绝启动。

两组 SDF 均实际注入 **1,773,775 条 path delay、114,988 条 timing check**，注入诊断和时序违规均为 0。通过 `xmsdfc` 编译实际 SDF 后，用 `-sdf_cmd_file` 回标 `tb_soc_pins.dut`，TT/MAXIMUM，保留 `NTC/RECREM/-negdelay` 配套模型配置与时序检查。模型全部潜在 specify 对象的百分比不是源 SDF 的请求覆盖率，不以它作为 100% 判据。

DMA 两次启动在三种仿真中都得到：参数装载 1872、累计输入装载 6960、应用总计 36342、推理/校验段 34371 个软件 mcycle；DMA CSR 累计忙周期为 2708，不能把它当作 NPU 核计算周期。正例各下载一次，再做两次复位运行。实际命令、哈希、注入统计和验收汇总见 [公开摘要](../test/2026-10-21/asic/summary.json)。

## 本轮完整 SoC 综合实测

以下数据来自包含启动等待与下降沿复位释放修复的 `eda/work/asic-resetfall/synthesis`，没有沿用 Lab 4 CPU 模板或旧网表的结果。

工艺为 TSMC180 TT、1.8 V、25 °C；主 SRAM 使用一个 `RA1SHD_2048x32M8` 宏，38 个 NPU 权重 bank 映射为标准单元。系统时钟 20 ns，JTAG 时钟 100 ns。

| 指标 | 实测值 |
| --- | ---: |
| 单元数量，含 SRAM 宏 | 174,420 |
| 单元面积，含 SRAM 宏 | 4,783,738.912 μm² |
| 主 SRAM 面积 | 401,443.591 μm² |
| NPU 子系统面积 | 3,422,255.334 μm² |
| 其中权重存储面积 | 1,307,248.186 μm² |
| CPU 面积 | 369,243.616 μm² |
| DMA 面积 | 58,614.035 μm² |
| 最差已约束 setup 裕量 | +0.141 ns |

最差已约束路径位于 CPU 的 ID/EX 逻辑。20 ns 对应 50 MHz 综合约束，+0.141 ns 不是布线后的频率保证。面积是映射单元面积，不是 Die 面积。

独立恢复本轮映射数据库检查 CP/CPN/CLK：253 个无时钟波形引脚均归因于 5 个 E=0、TE=0 的关闭 ICG 分支，数量与 Genus lint 一致。双向 CDC 各检查最差 10 条实际路径，均应用 12 ns 最大延时，最差裕量为 +11.065 ns、+11.086 ns。该审计说明约束命中和关闭分支来源，不代替形式 CDC 证明。

## 工具兼容修复与证据来源

Genus 19.17 必须先 `read_mmmc` 建立目标库域，再加载 LEF；本次已修复旧 Lab 4 流程的反序问题，没有屏蔽 `LBR-163`。初始探索运行曾在不支持的 `report_timing -early` 报告命令退出，随后从检查点导出兼容报告；**本轮最终 `asic-resetfall` 从 RTL 重新执行完整综合**，没有复用那份旧网表的通过记录。原始失败日志保留。

软件版本为 Genus 19.17-s144_1 和 Xcelium 21.09-s013。工艺库与 SRAM 模型由课程环境提供，不纳入仓库。

旧 `tb_soc` 的合成模型、真实模型 CPU、真实模型 DMA 三组功能回归也已通过，记录于 `eda/work/legacy-soc-adapter-regression-resetfall`。其内部端口预加载只作为兼容性回归；新计数排除了启动字准备的两拍，不能据此声称性能提升。软件 mcycle 基准、NPU 39/59 和 DMA 982 数据拍/62 突发的结果不变。

## 完整 SoC 的物理实现结果

2026-10-21，同一启动/复位修复后的完整 SoC 已完成 Innovus 的布局、CTS、route、finish 和 export，最终阶段 0 tool errors。实际 Die 为 3400.32 × 3400.32 μm，core 为 3100.16 × 3100.16 μm；最终 setup WNS +1.217 ns、hold WNS +0.018 ns，setup/hold 的 TNS 和违反端点、DRV 均为 0。最终布线 DRC、天线违规和 PG stub trim 剩余项均为 0，核心 PG 检查通过。

原生 IO 的两项 no-routing 提示与 34 处预期 Bond/PAD 覆盖保留在原报告中，通过独立原生 IO 轨、DEF/网表连接及覆盖几何检查验收；独立物理审计 8/8 PASS。最终 565,775 个实例均已放置，包括一个 SRAM、六个信号 PAD、28 个供电 PAD 和 34 个 Bond。物理实现数据、实例分类及证据边界见 [PNR 结果](pnr/RESULTS.md)，事前容量与 IO 适配依据保留在 [物理规划](PHYSICAL_PLAN.md)。

本页前述 SDF PASS 仍仅指综合后、布线前估计。**布线后 SDF 动态验收已 PASS：在 1000 ns 先复位后起钟协议下，MAX/MIN × synthetic/DMA 四个完整场景各完成两次 CPU 启动、2048 字下载回读，SDF/时序诊断为 0。** 原始 SDF 和仿真派生文件分别保留，转换核对见 PNR 结果；不能用静态时序或旧 SDF 的 PASS 替代新后仿。当前课程 TT 结果不代表全 PVT、独立形式等价、CDC 或 foundry 签核完成。
