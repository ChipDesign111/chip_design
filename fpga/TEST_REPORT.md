# FPGA 测试状态

当前操作入口见[新机器指南](README.md)，轻量证据见[报告目录](results/README.md)。工程、固件和原始测试输出已迁到仓库同级 `fpga_workspace`；构建和板测不会直接在仓库内运行。

## 当前固件与用户手动板测

当前 16-MAC INT22 固件包含 38 个 HAR 镜像及 24 个 HAR/RAW/CPU 配对包，覆盖 batch=1/2/3/4、33×65 尾块、K 分块、多层及 INT32 合并。[生成方法](firmware/README.md)与[批量测试](FIRMWARE_BATCH.md)均使用外部工作区。

用户在本次会话手动运行了以下两份固件，均检查全部 96 个字通过：

| 固件 | full_soc_cycles | 最后 NPU cycles | FC1/FC2 issue | DMA/MAC read/write/total overlap |
|---|---:|---:|---|---|
| `raw_full_b4_raw` | 12,349 | 730 | 512 / 0 | 434 / 465 / 465 |
| `raw_full_b4_cpu` | 180,232 | 0 | 0 / 0 | 0 / 0 / 0 |

同组完整 SoC 加速比为 **14.595×**。以上是用户提供的 GDB 实测记录，没有对应的新 bitstream SHA 或完整 62 镜像板测归档；不能据此声明整个批次通过。批测脚本运行后以实际 `summary.md` 为准。

## RTL 前仿与主机流程验证

启动修复保持 CPU RTL 不变：DM unavailable 接线、Boot ROM ready 条件回跳和调试 AXI 桥 NDM 复位域已通过专项仿真，见[启动与调试验证](../report/boot_debug_guard.md)。62/62 固件完整 SoC 前仿见[原始验证清单](results/20261119_boot_debug_guard/firmware_validation.json)。默认 HAR 硬件计数 2701、testbench 2706、NPU 952、FC1/FC2 512/64，DMA/MAC read/write/total overlap 为 466/499/500。新增 Boot 检查占 6 拍，NPU 计数保持不变。

本轮目录重构核对了全部 403 份迁移资产，182 份重新生成的 `.hex/.bin/.S` 与迁移前逐字节一致，另 1 份历史不完整装载 fixture 保留原件。16 项批测脚本和 9 项工作区离线检查通过，且用 Vivado 2019.1 在全新外部目录成功创建工程和 Clock Wizard。详细流程验证见[工作区迁移记录](results/20261119_workspace_migration/README.md)。本轮没有重新综合实现、生成新 bitstream 或操作真实 FPGA，下列 PPA 仅对应 2026-11-04 冻结版本。

## 最近板测冻结版本（20261104）

| 项目 | 状态 |
|---|---|
| RTL 逻辑基线 | `9970d6f`，验证快照 `1c265c0` |
| Bitstream | 已生成，无预装固件 |
| 20 MHz 时序 | WNS/WHS `+0.407/+0.034 ns` |
| Slice LUT | `17,625 / 20,800`，84.74% |
| RTL 回归 | 38/38 单元用例、24 条训练输入、完整 SoC PASS |
| 板级测试 | PASS |
| 扩展回归 | LED、连续复位、重复重配置、长时间运行均 PASS |

该冻结版本 bitstream SHA-256：

```text
bdf36e5888703ebc6905f3cd87a4f42b8256168484147baf97b966e9d47d326e
```

该冻结版本 canonical 固件 SHA-256：

```text
3f1dcd0eaf725269e52cd39e9e6917138e8f8ed932fa0d4f61fa81fe4175ee4b
```

2026-11-04 的 A7-35T 板测结果与 RTL 前仿一致：NPU 周期 `975`，
FC1/FC2 发射周期 `256/64`，DMA 读/写与 MAC 重叠均为 `278`。完整 SoC
周期实测为 `6368`（`0x000018E0`）；RTL 硬件口径为 `6364`，testbench
观测窗口为 `6369`，差异来自 debug-resume、计数器启动点和观测窗口不同。
PASS 标志为 `0xC0DEC0DE`，最终 PC 为 `0x80000470`。

LED、连续复位、重复 bitstream 重配置和长时间运行压力测试均通过。
SRAM 四字节写入最终得到 `0xDDCCBBAA`。逐项前仿/后仿对比、完整实测表和
测试边界见
[当前版本 TEST_REPORT.md](results/20261104_rtl-1c265c0_int22/TEST_REPORT.md)；
原始 GDB 记录见
[board_gdb_20261104.txt](results/20261104_rtl-1c265c0_int22/evidence/board_gdb_20261104.txt)。

## 历史版本

上一版板上 PASS 报告与已知 bitstream 哈希保存在
[20261101_rtl-fce9d9b_board-pass](results/20261101_rtl-fce9d9b_board-pass/README.md)。
旧固件已保存在外部完整归档中，其数值契约不能直接用于当前 RTL。
