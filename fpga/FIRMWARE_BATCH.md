# 一键依次测试全部固件

先按[新机器操作方法](README.md)在仓库外完成 `prepare`，烧写适配当前 RTL 的 runtime bitstream，并启动 OpenOCD。默认工作区为仓库同级 `fpga_workspace`，也可设 `FPGA_WORKSPACE`。

在已经连接板子的 WSL GDB 中执行（路径替换为自己的工作区）：

~~~gdb
source /path/to/fpga_workspace/gdb/test_all_firmware.gdb
~~~

入口由 `prepare` 生成，保存当前仓库与工作区的绝对路径，可从任意目录 source。迁移仓库位置后重新 `prepare`。它断开 GDB，经已有 OpenOCD 的 Tcl 端口 `127.0.0.1:6666` 批测，结束后重新连接 GDB `:3333` 并刷新寄存器缓存。使用外部 `python3`，不需要 GDB 内置 Python 或 PyTorch。

## 覆盖与执行顺序

- 38 个 HAR 镜像：32 个随机/边界批次、6 个 UCI 四样本批次。
- 8 个 HAR CPU/NPU 配对包：batch=1/2/3/4。
- 16 个 RAW/CPU 图包：batch=1/2/3/4，以及 33×65 尾块、K 分块、多层和 INT32 大累加。

合计 **62 个正常镜像**。`int8_selftest` 与 UCI 00 相同，不重复运行；`int8_partial_4k.bin` 是不完整装载 fixture，不参与正常推理测试。

每份执行：复位并 halt → 检查 Boot 状态为 0 → 顺序写满 2048 个字 → 核对装载覆盖、入口、初始标志和 tag → 提交启动码 → 明确从 `0x00010000` resume → 连续运行 1 秒 → halt → 检查结果、DPC、完整 SoC 周期与 NPU 计数。

配对包按 `board_manifest.json` 检查全部输入、中间值及输出。原 HAR 镜像回读 hidden、score、class，每样本 15 个字。CPU 包要求 NPU 计数为零；硬件包检查 FC1/FC2 发射数和 DMA/MAC overlap 的并集关系。运行前还核对固件、参考和 RTL 来源 SHA。

## 输出与计时

结果默认在外部工作区 `tests/fpga_board_时间戳/`：

| 文件 | 内容 |
|---|---|
| `summary.md` | 全部镜像结论、完整周期、最后任务的 NPU/DMA 指标、12 组配对加速比 |
| `summary.csv` | 每份结果、DPC、FC1/FC2、read/write/total overlap |
| `speedups.csv` | CPU 与硬件成对周期及加速比 |
| `result.json` | 测试环境、SHA、失败阶段、数值差异和已完成项目 |
| `镜像名.log` | OpenOCD 命令与实际内存回读，留在本机 |

加速比仅使用同组双方均 PASS 的 `CPU full_soc_cycles / 硬件 full_soc_cycles`。该计数从首次非 debug 取指到固件写 PASS/FAIL，不含 JTAG 装载与人工等待，与仿真的 BEGIN/END 应用区间不同。NPU/overlap 寄存器只保存最后一个任务，`total` 是读或写与 MAC 重叠的周期并集。`elapsed_seconds` 含装载和等待，不能用于算加速比。

脚本不会反复 halt 轮询完成标志，避免 PASS 前的调试暂停污染周期。1 秒后未完成即失败；较慢任务用 `--run-seconds` 重新完整运行。数值失败默认继续；复位、装载或通信错误停止批测并保存已完成结果。Ctrl+C 保存部分结果，并在连接可用时尝试 halt，无法确认时明确记录。

## 筛选和收录

在 GDB 中 `disconnect`，保持 OpenOCD 运行，从 WSL 仓库根目录执行：

~~~bash
python3 fpga/run.py test --group suite
python3 fpga/run.py test --only 'raw_full_b4_*'
python3 fpga/run.py test --run-seconds 2 --fail-fast
# 只离线列出，不连接板子
python3 fpga/firmware_batch.py --list
~~~

`--group legacy` 只跑原 38 份；`--only` 可重复给出名称或通配符。`--host/--port` 指定 Tcl 服务；自定义 `--out` 必须为仓库外的新目录。参数见 `python3 fpga/firmware_batch.py --help`。结束后可在 GDB 用 `target extended-remote :3333` 重新连接。

确认结果后，用 `python3 fpga/run.py collect --run /external/result/directory --name board_YYYYMMDD` 收录轻量报告；原始日志和所有可执行产物留在外部。

## 已验证范围

`python test/int8/test_firmware_batch.py` 的 16 项离线测试覆盖全部 62 镜像流程、原 16 个零输出的错误、错误 tag、部分装载、未完成运行、CPU/NPU 计数、overlap、Ctrl+C、部分汇总、Windows 报告文件占用，以及临时 TCP 服务的分片响应和 Tcl 错误。报告替换遇到短暂权限错误时有限重试；持续失败保留上一份完整 JSON 和新临时文件。本轮未用批测脚本操作真实 FPGA。用户手动测得的 RAW/CPU batch4 结果与历史板测分别记录在[测试状态](TEST_REPORT.md)。
