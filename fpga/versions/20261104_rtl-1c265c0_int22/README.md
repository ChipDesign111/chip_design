# 2026-11-04：当前 INT22 RTL

本版本对应当前 `rtl-dev` INT22 RTL 和最新的无预装 JTAG 流程。Vivado 已在
20 MHz 下完成综合、实现、布线和 bitstream 生成；RTL 与 SoC 回归通过，板级
测试尚待执行。

| 项目 | 当前结果 |
|---|---|
| RTL 逻辑基线 | `9970d6f` |
| 验证快照 | `1c265c0` |
| FPGA 模式 | 无预装，JTAG 装载固件 |
| 系统时钟 | 20 MHz |
| Setup WNS | `+0.407 ns` |
| Hold WHS | `+0.034 ns` |
| Slice LUT | `17,625 / 20,800`，84.74% |
| Slice Register | 13,855 |
| DSP48E1 | 40 |
| Block RAM Tile | 2 |
| 布线与 routed DRC | 全布通，0 errors |
| 板级状态 | 待执行 |

## 可交付产物

- Bitstream：[fpga_top.bit](artifacts/fpga_top.bit)
  - SHA-256：`bdf36e5888703ebc6905f3cd87a4f42b8256168484147baf97b966e9d47d326e`
- 当前 canonical 固件：[int8_selftest.bin](firmware/int8_selftest.bin)
  - SHA-256：`b639ab3ca002e73de3f79bd945d1760ec7111f05dfdb9c27efd7b05796303486`
- 38 个镜像清单：[image_manifest.json](firmware/image_manifest.json)
- 机器可读版本信息：[VERSION.json](VERSION.json)

`logs/synth_runme.log` 明确记录：

```text
Command: synth_design ... -generic SRAM_INIT_FILE=
Parameter SRAM_INIT_FILE bound to: 0
Synthesis finished with 0 errors, 0 critical warnings
```

因此本 bitstream 不包含预装固件。刷新固件后无需重新构建该 `impl_2`
bitstream；若另建预装版本，则必须在固件刷新后重新综合。

## 固件兼容性

本目录的固件由当前 `test/int8` 重新生成。旧版本固件在 `0x420` 仍检查
FC2 为 `batch*8`，而当前 RTL 输出 `batch*16`；同时 INT22 bias 和整数参考值
也已更新，所以上一版 `.hex/.bin` 不得用于本 bitstream。

当前 canonical 镜像 SHA-256：

```text
3f1dcd0eaf725269e52cd39e9e6917138e8f8ed932fa0d4f61fa81fe4175ee4b
```

## RTL 回归

当前快照已完成以下本地验证：

- 38/38 单元用例通过。
- 24 条训练输入通过。
- 完整 SoC 通过。
- RTL 观测窗口 `6369` 拍，硬件计数器 `6364` 拍。
- NPU `975` 拍，FC1/FC2 发射周期 `256/64`。
- DMA 读/写与 MAC 重叠均为 `278` 拍。

测试证据见 [soc.log](evidence/soc.log) 和 [result.json](evidence/result.json)。

## 板上待测

按上一版无预装 JTAG 流程，预计硬件 SoC 周期为 `6365`；实际值必须以本次
板上读取为准。板测通过后，应把本目录状态从 `board_pending` 更新为
`board_pass`，并记录原始 GDB、NPU MMIO 和 LED 观测结果。
