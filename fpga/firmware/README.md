# FPGA 固件生成器

本目录只保存生成器和验证器源码。`.hex/.bin`、manifest、汇编清单和 `check.gdb` 由脚本在外部工作区生成，不跟踪到 Git。

从仓库根目录执行 `python fpga/run.py prepare --compiler-python /path/to/python-with-torch`。默认输出为仓库同级 `fpga_workspace/firmware/`；用 `FPGA_WORKSPACE` 或 `--workspace` 改位置。完整环境和上板步骤见[新机器操作方法](../README.md)。

| 文件 | 作用 |
|---|---|
| [generate_images.py](generate_images.py) | 生成 32 个随机/边界 HAR、6 个 UCI 四样本镜像，以及同 UCI 00 的默认自检别名 |
| [generate_suite.py](generate_suite.py) | 用现有 HAR 和 PyTorch FX/RAW 后端生成 24 个 CPU/硬件配对包及 GDB 数值检查脚本 |
| [validate_images.py](validate_images.py) | 验证 hex/bin、大小、源码 SHA、CPU/RAW 张量和参考；可检查 SRAM dump 或跑全部 62 份 SoC 仿真 |

所有生成接口默认写仓库外，显式指定仓库内输出会报错。需要分别生成时：

~~~bash
python fpga/firmware/generate_images.py --output-dir /external/work/firmware
python-with-torch fpga/firmware/generate_suite.py --output-dir /external/work/firmware/suite
python fpga/run.py validate --workspace /external/work
~~~

## 镜像和数值契约

legacy 镜像为 8 KiB 小端二进制，对应 2048 行 32 位 hex。`int8_selftest` 等于 `int8_uci_00_batch4`；`int8_partial_4k.bin` 只是不完整装载测试 fixture。生成的 `image_manifest.json` 记录每份 SHA、batch、代码大小、停止 PC 和来源 SHA。

| 配对包前缀 | 形状 | batch | 验证内容 |
|---|---|---|---|
| `har_b1`…`har_b4` | 64→32→6 | 1/2/3/4 | `_cpu` / `_npu`，原 HAR hidden/score/class 及 INT22 wrap/requant |
| `raw_full_b1`…`raw_full_b4` | 64→32 | 1/2/3/4 | `_cpu` / `_raw`，不同输入、SRAM 预打包、batch 权重复用 |
| `raw_tail_b4` | 65→33 | 4 | 32×64 硬件块与 CPU 右侧/底部尾项 |
| `raw_k_split_b4` | 128→32 | 4 | K 分块及 CPU INT32 合并 |
| `raw_multi_b2` | 64→32→64 | 2 | 多层、中间值、ReLU/Tanh 与 CPU/NPU 协作 |
| `raw_wide_b3` | 128→32 | 3 | 大 bias、超过 INT22 的完整结果、CPU INT32 合并后量化 |

RAW 图的层间输出是有符号 INT8，与保留 INT32 最终输出的原整数 GEMV 接口不同。每个配对包有 `firmware.hex/bin`、`firmware.S`、`board_manifest.json` 和 `check.gdb`；RAW 另有编译布局和参考张量，HAR 另有基准布局及 expected 文件。

RAW 的 `0xC0DEC0DE` 只表示完成，必须用对应 `soc-check-result` 验收数值；它从真实 SRAM 检查全部输入、中间层和输出。HAR 固件内部自检，并提供 GDB 再读回。板测步骤及完整周期、DMA/MAC overlap 口径见[批量板测](../FIRMWARE_BATCH.md)。

在外部工作区运行 GDB 时，可 `dump binary memory raw_full_b4_sram.bin 0x80000000 0x80002000`，再从仓库根目录离线核对：

~~~bash
python fpga/firmware/validate_images.py --package /external/work/firmware/suite/raw_full_b4_raw --dump /external/work/raw_full_b4_sram.bin
~~~

本轮迁移前的 62/62 完整 SoC 验证记录保留于[固件验证报告](../results/20261119_boot_debug_guard/firmware_validation.json)。默认 HAR 硬件完整计数 2701、testbench 2706、NPU 952、FC1/FC2 512/64、read/write/total overlap 466/499/500；这是对应 RTL 的前仿，板测应单独记录。
