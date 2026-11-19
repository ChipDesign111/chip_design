# 2026-11-19：62 份固件 FPGA 批测

用户于北京时间 17:24:02–17:55:15 执行一键批测，结果 **62/62 PASS，失败 0，未完成 0**。离线核对了全部 62 份日志 SHA、固件及当前源码身份、3154 个结果字和 12 组加速比；工程、固件和原始逐命令日志保留在外部工作区。

## 覆盖与验收

| 范围 | 数量 | 结果 |
|---|---:|---|
| 原 HAR 随机/边界及 UCI 固件 | 38 | 全部 PASS |
| HAR CPU/NPU 配对，batch=1/2/3/4 | 8 | 全部 PASS |
| RAW/CPU 配对，全块、尾块、K 分块、多层、大累加 | 16 | 全部 PASS |
| SRAM/MMIO 数值检查 | 3154 个字 | 全部匹配 |
| 原始日志 SHA | 62 份 | 全部匹配 |

每份均通过复位状态 `0`、完整装载 `0x800`、提交状态 `0x2800`、PASS、停止 PC 和结果检查；配对包还检查身份 tag 与 END。12 份纯 CPU 镜像的 NPU 计数全部为零，50 份硬件镜像的发射数与对应任务匹配，DMA/MAC read/write/total overlap 均满足并集关系。

## 完整 SoC 加速比

计时为首次非 debug 取指到固件写 PASS/FAIL，包含 Boot、CPU 配置、结果搬运和固件自检；不包含 JTAG 装载、人工等待或运行后的脚本数值读回。加速比为同组 CPU 周期除以硬件周期。

| 配对 | CPU 周期 | 硬件周期 | 加速比 |
|---|---:|---:|---:|
| HAR batch1 | 51,945 | 1,792 | 28.99× |
| HAR batch2 | 76,675 | 2,337 | 32.81× |
| HAR batch3 | 129,000 | 2,856 | 45.17× |
| HAR batch4 | 154,660 | 3,370 | 45.89× |
| RAW full batch1 | 36,996 | 3,969 | 9.32× |
| RAW full batch2 | 77,724 | 6,775 | 11.47× |
| RAW full batch3 | 116,264 | 9,568 | 12.15× |
| RAW full batch4 | 180,229 | 12,349 | 14.59× |
| RAW 33×65 尾块 batch4 | 187,168 | 26,361 | 7.10× |
| RAW K 分块 batch4 | 254,107 | 19,256 | 13.20× |
| RAW 多层 batch2 | 189,366 | 83,497 | 2.27× |
| RAW 大累加 batch3 | 186,747 | 14,947 | 12.49× |

此前 HAR 的 58.78× 和 RAW 的应用周期采用 BEGIN/END 区间，不能与本表混用。HAR batch4 的应用区间前仿为 2612 拍；本次 3370 拍还包含区间外的启动、结果 golden 自检和统计。原默认 HAR 自检在本次板测为 2700 拍，它直接比较 NPU 结果，与先将结果保存到 SRAM 的配对固件不同。

## NPU 与 overlap

| 镜像 | 完整 SoC | 最后 NPU cycles | FC1 / FC2 issue | read / write / total overlap |
|---|---:|---:|---|---|
| 原 UCI 00 batch4 | 2700 | 952 | 512 / 64 | 466 / 499 / 500 |
| HAR batch4 NPU | 3370 | 952 | 512 / 64 | 466 / 499 / 500 |
| RAW full batch4 | 12349 | 730 | 512 / 0 | 434 / 465 / 465 |

完整 62 项数据见 [summary.md](summary.md) 和 [summary.csv](summary.csv)。NPU/DMA 寄存器只保存最后一个硬件任务，不能当作多块或多层网络的累加值；total 是去重后的重叠周期并集。

与[当前固件 RTL 前仿](../20261119_boot_debug_guard/firmware_validation.json)比较，46 份 HAR（含 8 份配对包）的板端完整周期均少 1 拍，NPU、FC1/FC2 和全部 overlap 计数逐项一致。RAW 仿真的部分计数是整图累加，未与板上最后任务计数直接等同。逐项比较见 [audit.json](audit.json)。

## 证据与边界

- [result.json](result.json)：原始批测结构化结果，保留用户运行的原字节。
- [summary.md](summary.md)、[summary.csv](summary.csv)、[speedups.csv](speedups.csv)：原始汇总与全部加速比。
- [receipt.json](receipt.json)：外部运行目录和收录文件 SHA。
- [audit.json](audit.json)：离线复核、62 份日志身份和前仿周期对照结论。
- [镜像清单](inputs/image_manifest.json)、[配对包清单](inputs/suite_manifest.json)：本次使用的固件及来源 SHA，原字节保留。

外部原始目录为 `fpga_workspace/tests/fpga_board_20261119_172402_151924/`。报告使用现有板卡的周期计数，批测没有记录实际烧写的 bitstream SHA，因此不把某个磁盘 bitstream 推断为本次板上文件。此次覆盖正常固件执行及每次复位装载；未新增 PPA、错误启动码、冷启动专项或压力测试结论。历史资源与时序仍按对应版本报告记录。
