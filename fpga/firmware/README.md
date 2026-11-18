# 当前 RTL 的 FPGA 测试固件

2026-11-19 更新，目标为当前 **16 个共享 INT8 乘法器、INT22 累加器**的 RTL。
所有正常镜像都占完整 8 KiB SRAM：`.hex` 为 2048 行 32 位字，`.bin` 为
8192 字节小端数据，可直接用于 Vivado 预装载或 GDB/JTAG 装载。

本轮 **62/62 份固件通过完整 SoC 前仿**；RAW/CPU 图包的全部张量经 SBA
读回比较通过。启动保护修复后重新绑定来源并复验，固件机器码、镜像及 GDB
检查脚本保持逐字节一致；详见 [启动与调试验证](../../report/boot_debug_guard.md)。
**尚未生成此启动修复的新 bitstream，也未上板验证**。
必须使用当前 RTL 构建的 bitstream。2026-11-04 冻结 bitstream 的 HAR 发射
周期和 RAW 接口均不适合直接验收这批固件；其板测结果仍见
[冻结版本](../versions/20261104_rtl-1c265c0_int22/README.md)。

## 默认自检与原有回归

默认入口仍为 [int8_selftest.hex](int8_selftest.hex) 和
[int8_selftest.bin](int8_selftest.bin)，内容与 UCI 00、batch=4 镜像相同。
保持原有 HAR `64→32→6`、`reuse8` 搬运流程，CPU 逐项比较全部 hidden、
6 个 score、class，并检查 tile 加载次数和 FC1/FC2 发射次数。
当前硬件期望 `FC1=128×batch`、`FC2=16×batch`。

| 镜像 | 数量 | 覆盖内容 |
|---|---:|---|
| `int8_random_00_batch4` … `int8_random_31_batch2` | 32 | batch=1/2/4，INT22/bias 边界、requant、MULT=0、跨 4 KiB 的权重地址 |
| `int8_uci_00_batch4` … `int8_uci_05_batch4` | 6 | 训练模型固定的 24 条 UCI 输入 |
| `int8_selftest` | 上述 UCI 00 的别名 | 首次上板推荐入口 |

每个镜像现在都同时生成 `.hex` 和 `.bin`，避免只更新 hex 后误装旧 bin。
[image_manifest.json](image_manifest.json) 记录来源 SHA、每个文件的 SHA、代码大小、
batch 和停机 PC。默认固件代码为 1520 B，停机自循环为 **`0x800005EC`**。
`int8_partial_4k.bin` 仅保留为历史的不完整装载 fixture，不是可启动固件。

默认固件的本轮前仿基线：完整硬件 SoC **2701 拍**（testbench 观测 2706 拍），
NPU 952 拍，FC1/FC2 发射 512/64 拍，DMA/MAC read、write、total overlap
分别为 **466、499、500 拍**。相对启动修复前 2695 拍，Boot 就绪检查增加
6 拍；这些是当前 RTL 前仿数据，板端结果需另行记录。

## CPU/NPU 配对测试包

[suite/suite_manifest.json](suite/suite_manifest.json) 列出额外的 **24 个固件包**。
每组 CPU/NPU 使用相同的输入、逻辑权重、量化契约和预期结果，便于在同一
bitstream、同一时钟下比较完整 SoC 周期。

| 包目录（前缀） | 输入/输出 | batch | 后端 | 验证内容 |
|---|---|---:|---|---|
| `har_b1` … `har_b4` | 64→32→6 | 1/2/3/4 | `_cpu` / `_npu` | 原 HAR 数值、hidden/score/class，结果写回 SRAM 后 CPU 自检 |
| `raw_full_b1` … `raw_full_b4` | 64→32 | 1/2/3/4 | `_cpu` / `_raw` | RAW 全块、各样本不同输入、batch 内权重复用 |
| `raw_tail_b4` | 65→33 | 4 | `_cpu` / `_raw` | 一个 32×64 NPU 块，CPU 补齐右侧/底部尾项 |
| `raw_k_split_b4` | 128→32 | 4 | `_cpu` / `_raw` | K 方向分块，CPU INT32 合并部分和 |
| `raw_multi_b2` | 64→32→64，含 ReLU/Tanh | 2 | `_cpu` / `_raw` | 多层中间结果、CPU 激活和 NPU/CPU 协作 |
| `raw_wide_b3` | 128→32 | 3 | `_cpu` / `_raw` | 大 bias / 超过 INT22 的完整累加结果，CPU INT32 合并后量化 |

RAW 包由当前 PyTorch 前端和当前分支 RAW 后端生成，采用已实现的 SRAM 预打包权重。
batch=2/3/4 的全块复用同一份权重 DMA，每个 32×64 块只启动一次硬件批任务。
RAW 图的层间输出为有符号 INT8；它与保留 INT32 最终输出的原整数 GEMV 接口
有不同的输出契约。HAR CPU/NPU 则保持原 HAR 的 INT22 wrap 和 requant 契约。

每个目录包含：

- `firmware.hex` / `firmware.bin`：可装载镜像；`firmware.S`：RV32 指令清单。
- `board_manifest.json`：镜像身份、代码大小、结果地址、完整预期值和文件 SHA。
- `check.gdb`：检查镜像身份、PASS 状态和数值结果的 GDB 命令。
- RAW 的 `manifest.json` / `reference.json`：编译布局、后端划分、量化后的全部张量。
- HAR 的 `benchmark_meta.json` / `expected.hex` 等：配对前仿所需的结果与监控布局。

**RAW 固件的 `0xC0DEC0DE` 表示执行完成；数值验收还必须运行 `soc-check-result`。**
RAW 镜像没有把 golden 再塞进有限 SRAM；GDB 从真实 SRAM 比较全部输入、中间层和
最终输出。HAR 包在固件内自检全部结果，也提供 GDB 再次读回。LED 常亮在 RAW 中
仅表示完成，不能单独作为数值通过证据。

## 上板操作

完整连接、复位和 OpenOCD 操作见 [FPGA 使用说明](../README.md)。以下命令以
GDB 当前工作目录为 `fpga/`、SoC 已复位且 CPU 已 halt 为前提：

```gdb
source load_soc_image.gdb
monitor reset halt
maintenance flush register-cache
soc-boot-status
soc-load-bin firmware/suite/raw_full_b4_raw/firmware.bin
soc-commit-image
monitor resume 0x00010000
shell sleep 1
monitor halt
maintenance flush register-cache
source firmware/suite/raw_full_b4_raw/check.gdb
soc-check-result
soc-full-cycles
soc-npu-counters
```

期望出现 `FPGA_CHECK_PASS raw_full_b4_raw`；`$soc_check_errors` 应为 0。
然后复位 SoC，改装 `raw_full_b4_cpu`，同时换用该目录的 `check.gdb`，重复运行。
每次换固件都要复位、重写全部 2048 个字并提交，复位不会清空 SRAM。

板上加速比按 **CPU 的 `soc-full-cycles` / NPU 的 `soc-full-cycles`** 计算。
硬件计数地址为 `0x00010038`，从第一次非 debug 取指计到写 PASS/FAIL；不含
JTAG 装载和人工等待时间。前仿报告中的 `benchmark_cycles` 只量 BEGIN/END，
与板上完整计数窗口不同，应分开记录。

`soc-npu-counters` 会打印 DMA/MAC 的 read、write、total overlap。
这些寄存器只保存**最后一个硬件任务**；多块 RAW 网络不能把它们当成整网累计。
`total` 是读或写与 MAC 重叠的周期并集，不能直接用 read+write 替代。
纯 CPU 包不启动 NPU，不能把 NPU 计数器作为其性能指标。

也可以离线检查实际 SRAM dump：

```gdb
dump binary memory raw_full_b4_sram.bin 0x80000000 0x80002000
```

随后从仓库根目录运行：

```powershell
.venv/Scripts/python.exe fpga/firmware/validate_images.py --package fpga/firmware/suite/raw_full_b4_raw --dump fpga/raw_full_b4_sram.bin
```

## 重新生成和验证

从仓库根目录运行。第一步只需普通 Python；第二步需要安装了 PyTorch 的编译环境：

```powershell
.venv/Scripts/python.exe fpga/firmware/generate_images.py
tools/local/compiler_env/Scripts/python.exe fpga/firmware/generate_suite.py
.venv/Scripts/python.exe fpga/firmware/validate_images.py
```

如需重跑这批实际镜像的完整 CPU/SoC 仿真，使用一个尚不存在的输出目录：

```powershell
.venv/Scripts/python.exe fpga/firmware/validate_images.py --simulate --vsim D:/modeltech64_2019.2/win64/vsim.exe --out test/int8/runs/fpga_firmware_NEW
```

验证器检查 hex/bin 一致、大小、来源哈希、CPU/RAW 张量一致性、预期读回内容。
完整仿真运行实际生成的 38+24 份镜像，沿用现有测试台检查真实 CPU 运算、
输出写回、DMA/RAW 调度和硬件计数；RAW 全部张量还经 SBA 读回。
本轮结果保存在 [validation.json](validation.json)。
