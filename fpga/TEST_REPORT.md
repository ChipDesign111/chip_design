# FPGA 测试状态

FPGA 测试证据按不可覆盖版本归档，入口见
[fpga/versions](versions/README.md)。最近完成板测的冻结版本为
[20261104_rtl-1c265c0_int22](versions/20261104_rtl-1c265c0_int22/README.md)。

2026-11-09 活动固件已更新为 `scheduled4`，完成固定 RTL 的 CPU 仿真验证。
本次没有重新生成 FPGA bitstream 或重新板测；下列板级结果仅对应冻结版本。

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

当前 bitstream SHA-256：

```text
bdf36e5888703ebc6905f3cd87a4f42b8256168484147baf97b966e9d47d326e
```

当前 canonical 固件 SHA-256：

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
[当前版本 TEST_REPORT.md](versions/20261104_rtl-1c265c0_int22/TEST_REPORT.md)；
原始 GDB 记录见
[board_gdb_20261104.txt](versions/20261104_rtl-1c265c0_int22/evidence/board_gdb_20261104.txt)。

## 历史版本

上一版板上 PASS 报告、旧固件和已知 bitstream 哈希已冻结在
[20261101_rtl-fce9d9b_board-pass](versions/20261101_rtl-fce9d9b_board-pass/README.md)。
旧固件不兼容当前 RTL，不得与当前 bitstream 混用。
