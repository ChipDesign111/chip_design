# FPGA 测试状态

FPGA 测试证据按不可覆盖版本归档，入口见
[fpga/versions](versions/README.md)。当前活动版本为
[20261104_rtl-1c265c0_int22](versions/20261104_rtl-1c265c0_int22/README.md)。

## 当前版本

| 项目 | 状态 |
|---|---|
| RTL 逻辑基线 | `9970d6f`，验证快照 `1c265c0` |
| Bitstream | 已生成，无预装固件 |
| 20 MHz 时序 | WNS/WHS `+0.407/+0.034 ns` |
| Slice LUT | `17,625 / 20,800`，84.74% |
| RTL 回归 | 38/38 单元用例、24 条训练输入、完整 SoC PASS |
| 板级测试 | 待执行 |

当前 bitstream SHA-256：

```text
bdf36e5888703ebc6905f3cd87a4f42b8256168484147baf97b966e9d47d326e
```

当前 canonical 固件 SHA-256：

```text
3f1dcd0eaf725269e52cd39e9e6917138e8f8ed932fa0d4f61fa81fe4175ee4b
```

板测时应预期 NPU 周期 `975`、FC1/FC2 发射周期 `256/64`，
DMA 读/写与 MAC 重叠均为 `278`。完整 SoC 周期以实测为准；按无预装
debug-resume 口径预计为 `6365`。

## 历史版本

上一版板上 PASS 报告、旧固件和已知 bitstream 哈希已冻结在
[20261101_rtl-fce9d9b_board-pass](versions/20261101_rtl-fce9d9b_board-pass/README.md)。
旧固件不兼容当前 RTL，不得与当前 bitstream 混用。
