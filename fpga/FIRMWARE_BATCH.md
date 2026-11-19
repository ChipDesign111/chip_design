# 一键依次测试全部固件

保持现有 OpenOCD 运行。在你当前已经连接板子的 WSL GDB 中，从 `fpga/` 目录执行：

```gdb
source test_all_firmware.gdb
```

入口会断开 GDB，让批测脚本独占操作 CPU，然后通过现有 OpenOCD Tcl 端口
`127.0.0.1:6666` 依次测试；结束后重新连接 GDB `:3333`，刷新寄存器缓存。
不需要 GDB 内置 Python，使用 WSL 自带的 `python3`，也不需要 PyTorch。
使用你当前已经验证的无预装载 bitstream；本次只增加主机脚本。

若 GDB 当前目录不同，先执行：

```gdb
cd /mnt/d/LiChade/PKU/major/AdvanceChip/chip_design/chip_design/fpga
source test_all_firmware.gdb
```

## 默认覆盖

- 38 个原 HAR 镜像：32 个随机/边界批次、6 个 UCI 四样本批次。
- 8 个 HAR CPU/NPU 配对包：batch=1/2/3/4。
- 16 个 RAW/CPU 图包：batch=1/2/3/4，33×65 尾块、K 分块、多层和 INT32 大累加。

总计 **62 个正常镜像**。`int8_selftest` 与 UCI 00 完全相同，不重复运行；
`int8_partial_4k.bin` 是历史不完整装载 fixture，不属于可完成推理的固件。

每份固件执行：

```text
reset halt → 确认 Boot 状态为 0
→ 顺序写满 2048 个字 → 确认 loaded_words=2048、ready=0
→ 校验入口指令、初始完成标志和配对包 tag
→ 提交 boot key → 确认 ready=1
→ resume 0x00010000 → 连续运行 1 秒 → halt
→ 检查 PASS、全部数值、DPC、完整 SoC 周期和最后一个 NPU 任务的计数
```

配对包直接复用 `board_manifest.json` 的检查地址、预期值和 mask，与手工
`check.gdb` 的数值约定一致。原 HAR 镜像还从 NPU MMIO 回读全部 hidden、score
和 class，与该镜像内的 golden 比较，每样本 15 个字。纯 CPU 包要求 NPU
计数全部为零；硬件包检查 FC1/FC2 发射数及 DMA/MAC overlap 的并集关系。

运行前会复用原验证器检查全部文件、参考结果和 RTL 来源 SHA。每个镜像重新
复位、完整装载并明确从 Boot 入口启动，不沿用前一镜像的 DPC。

## 结果与计时口径

终端打印每份固件的 PASS/FAIL、检查字数和完整 SoC 周期。结果默认保存在：

```text
test/int8/runs/fpga_board_时间戳/
```

| 文件 | 内容 |
|---|---|
| `summary.md` | 全部镜像结果、周期、最后任务的 NPU/DMA 指标，以及 12 组配对加速比 |
| `summary.csv` | 逐镜像结果、周期、DPC、FC1/FC2 和 read/write/total overlap |
| `speedups.csv` | CPU/硬件成对周期及加速比 |
| `result.json` | 结构化结果、文件 SHA、失败阶段、数值差异和中断后的已完成项目 |
| `镜像名.log` | 对应的 OpenOCD 命令和实际内存回读 |

加速比只使用同组 CPU 与硬件包均 PASS 的结果，计算
`CPU full_soc_cycles / NPU full_soc_cycles`，不是 BEGIN/END 仿真区间。
NPU 和 overlap 只表示最后一个硬件任务，不代表多块网络的累计值。
每项的 `elapsed_seconds` 包括 JTAG 装载和等待，不能用于计算加速比。

脚本运行时不会反复 halt 查询完成标志，避免在 PASS 前把 JTAG 暂停时间
混入硬件计数。如果 1 秒后仍未完成，该次标为失败且不参与加速比；需要较长
运行时间时，用下述 `--run-seconds` 重新完整装载测试。

数值失败默认继续测试下一份；`--fail-fast` 可在首个数值失败时停止。
复位、装载或通信错误会停止批测并保存已有结果，避免后续结果建立在失效的
目标状态上。Ctrl+C 也会保存已完成结果，并在连接可用时尝试让运行中的 CPU
halt；通信中断导致无法确认 halt 时会明确记录。

## 自定义范围

先在 GDB 中 `disconnect`，保持 OpenOCD 运行，再从 WSL 仓库根目录执行：

```bash
# 只测试 24 个配对包
python3 fpga/firmware_batch.py --run --group suite

# 只测试刚才的 RAW batch4 / CPU 配对
python3 fpga/firmware_batch.py --run --only 'raw_full_b4_*'

# 连续运行更久，指定全新的输出目录
python3 fpga/firmware_batch.py --run --run-seconds 2 --out test/int8/runs/board_NEW

# 仅离线检查并列出镜像，不连接板子
python3 fpga/firmware_batch.py --list
```

`--group legacy` 只跑原 38 份；`--only` 支持重复指定名称或通配符。
其他参数见 `--help`，可通过 `--host`、`--port` 设置 Tcl 服务地址；端口应为
Tcl 的 6666，而不是 GDB 的 3333。自定义运行后可在 GDB 执行
`target extended-remote :3333` 重新连接。

## 验证状态

```powershell
.venv/Scripts/python.exe test/int8/test_firmware_batch.py
```

14 项离线测试已通过，包含 62 镜像的控制流程、原 16 个零输出的失败检测、
错误 tag、部分装载、未完成运行、CPU/NPU 计数、overlap、Ctrl+C、失败汇总，
以及通过本地临时 TCP 服务验证分片响应、完整 8 KiB 装载和 Tcl 错误。
还使用实际 OpenOCD 离线验证 Tcl catch/format，使用实际不带 Python 的
RISC-V GDB 验证外部 Python 清单调用。

这些是脚本与协议测试。本次未运行该脚本操作真实 FPGA，不将离线 fixture 的
PASS 当作 62 份固件的板测结论；执行后以你生成的 `summary.md` 为准。
