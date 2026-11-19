# FPGA 测试报告

这里只保存可审阅的 Markdown、JSON、CSV、资源/时序报告和少量原始文本证据。工程、IP、bitstream、固件和逐命令运行日志留在仓库外的工作区；新机器按 [FPGA 操作指南](../README.md) 生成，测试后用 `python fpga/run.py collect` 收录一份新报告。

| 记录 | 范围 | 结论 |
|---|---|---|
| [board_20261119_172402](board_20261119_172402/README.md) | 用户执行当前固件完整板测：38 HAR + 24 配对包，3154 个结果字、12 组加速比 | **62/62 PASS**，原始结果与离线复核已归档 |
| [20261119_workspace_migration](20261119_workspace_migration/README.md) | 外部工作区、原资产 SHA、固件重建、脚本与 Vivado 工程创建 | 主机流程验证；未重新板测 |
| [20261119_boot_debug_guard](20261119_boot_debug_guard/firmware_validation.json) | 当前启动修复后的 62 份实际固件 SoC 前仿 | 62/62 PASS；原验证字节保留 |
| [20261104_rtl-1c265c0_int22](20261104_rtl-1c265c0_int22/README.md) | `9970d6f` 逻辑、`1c265c0` 验证快照，INT22、32-MAC | 20 MHz 构建与 A7-35T 板测 PASS |
| [20261101_rtl-fce9d9b_board-pass](20261101_rtl-fce9d9b_board-pass/README.md) | `fce9d9b`，INT32、32-MAC | 历史板测 PASS；原 bitstream 曾被覆盖 |

完整批测及此前手动 RAW/CPU batch4 实测见[当前测试状态](../TEST_REPORT.md)。历史板测数据只代表对应提交。

2026-11-19 从原 `fpga/versions` 迁出完整归档，报告子集保留在此。历史 `VERSION.json`、manifest、rpt 与证据 JSON 保持原字节，其中路径、SHA 和状态描述属于当时的文件布局；不代表产物仍在仓库内，也不代表当前 RTL。完整历史文件在迁移机器外部工作区的 `archives/<原版本名>/`。

新报告使用独立目录，保留输入身份、时钟、测试环境、计时口径和已知限制。不要用离线 fixture 结果替代实际板测结论。
