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
| [20261104_rtl-1c265c0_int22](20261104_rtl-1c265c0_int22/README.md) | `9970d6f` 逻辑，`1c265c0` 测试快照 | 板测待执行 | 当前 INT22、`CUT_SLV_AX`、串行 FC2/Argmax 版本；20 MHz 构建和 RTL 回归通过 |

当前活动版本记录在 [ACTIVE_VERSION](ACTIVE_VERSION) 中。
