# FPGA 版本归档

`fpga/versions/` 保存不可覆盖的 FPGA 快照。每次板上测试或形成一份可交付
bitstream 后，都新建一个版本目录，不再复用或覆盖旧版本目录。

目录名格式：

```text
YYYYMMDD_rtl-<rtl-commit>_<status>
```

每个版本至少包含：

- `VERSION.json`：源提交、时钟、bitstream、固件、构建和测试状态。
- `README.md`：版本摘要、证据入口和已知限制。
- `artifacts/` 或 `firmware/`：该版本对应的可交付产物。
- `reports/`、`logs/`、`evidence/`：时序、资源、综合实现日志和测试证据。

当前工作区 `fpga/firmware/`、`fpga/final_project/` 是可继续构建的活动目录；
验证完成后将对应产物复制到新的版本目录。版本目录建立后应视为只读。

## 版本列表

| 版本 | RTL 基线 | 板级状态 | 摘要 |
|---|---|---|---|
| [20261101_rtl-fce9d9b_board-pass](20261101_rtl-fce9d9b_board-pass/README.md) | `fce9d9b` | PASS | 上一版 20 MHz、32-MAC、INT32 累加器板上测试；旧 bitstream 原件缺失，但报告、哈希和固件快照保留 |
| [20261104_rtl-1c265c0_int22](20261104_rtl-1c265c0_int22/README.md) | `9970d6f` 逻辑，`1c265c0` 测试快照 | PASS | 当前 INT22、`CUT_SLV_AX`、串行 FC2/Argmax 版本；20 MHz 构建、RTL 回归和 A7-35T 板测通过 |
| [20261120_rtl-0b5e34d_camera-debug-pending](20261120_rtl-0b5e34d_camera-debug-pending/README.md) | `0b5e34d`，RTL未改 | 构建/配置PASS；推理NOT_RUN | RAW多轮演示硬件；18141 LUT，20 MHz时序通过；CPU JTAG全0待排查，不能作为已板测版本 |
| [20261120_rtl-0b5e34d_live-board-pass](20261120_rtl-0b5e34d_live-board-pass/README.md) | `0b5e34d`，RTL未改 | 数值板测PASS | 同一RAW bitstream，最终主机源码下100轮算术+12轮工程模型回传均正确；真人采样/准确率待验证 |

当前活动版本记录在 [ACTIVE_VERSION](ACTIVE_VERSION) 中。
该指针现指向RAW多轮数值板测通过版本；历史debug-pending目录仍保留当时失败状态，不覆盖。
