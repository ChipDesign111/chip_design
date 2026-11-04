# 2026-11-01：上一版板上测试

这是上一版 FPGA 的冻结归档，对应 `rtl-dev` 上共享 32-MAC、INT32 累加器的
逻辑基线 `fce9d9b`。Vivado 构建快照提交为 `9485538`，最终 bitstream 在
2026-11-01 完成板级 PASS。

| 项目 | 结果 |
|---|---|
| 系统时钟 | 20 MHz |
| 板级状态 | PASS |
| NPU 周期 | 908 |
| DMA 读/MAC 重叠 | 270 |
| DMA 写/MAC 重叠 | 269 |
| 无预装 JTAG SoC 周期 | 5105 |

## 产物

- 完整原始测试报告：[TEST_REPORT_20261101.txt](evidence/TEST_REPORT_20261101.txt)
- 旧固件与 JTAG 二进制：[firmware](firmware/)
- 机器可读版本信息：[VERSION.json](VERSION.json)

旧 bitstream 的 SHA-256 为
`e4247f4ae84d01a8a6a1ad556d2d4ae79444c49d14d454f099828f1e24c917b6`，
但该工作区文件已在 2026-11-04 重建时被覆盖，当前无法恢复原件。因此本目录
只声明保留该版本的报告、哈希和固件证据，不提供被误标为旧板的替代 bitstream。

## 兼容性

本目录固件属于历史版本。其 FC2 发射周期检查仍按旧调度编写，也没有当前
INT22 bias/reference 更新，不能与 2026-11-04 的新 RTL bitstream 混用。
