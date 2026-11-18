# HAR 模式相对纯 CPU 的加速比

2026-11-18，在当前 `feat/int22-gemv-runtime` 分支的完整 CV32E40P / AXI / 8 KiB SRAM SoC 上实测。使用原训练模型 `64 → 32 → 6`、原量化参数，以及 `seed=10000` 的第一组 UCI 固定输入。batch=1/2 分别取同一组四样本的前 1/2 条。

| batch | 纯 CPU 周期 | HAR 端到端周期 | CPU/HAR 加速比 |
|---:|---:|---:|---:|
| 1 | 51,613 | 1,525 | **33.84×** |
| 2 | 76,104 | 1,918 | **39.68×** |
| 4 | 153,536 | 2,612 | **58.78×** |

加速比为 `CPU 周期 / HAR 周期`。这里的 HAR 周期包含 CPU 配置、输入搬运、DMA/NPU 执行、轮询，以及将所有 hidden、六类分数和类别写回 SRAM；不能用 NPU 内核的 952 拍替代 batch=4 的端到端 2,612 拍。

## 对照口径

- CPU 与 NPU 使用相同的逻辑权重、偏置、输入和量化参数。CPU 权重为普通行优先排列，NPU 权重保持现有离线打包格式，计时内均不转换权重。
- 纯 CPU 使用现有四项展开的 RV32IM 标量点积内核，执行两层全连接、INT22 回绕、ReLU、精确 64 位乘积重定标和有符号 argmax；并列时选择较小类别索引。基准没有使用额外的 SIMD/DSP 优化。
- HAR 使用原 `MODE=0` 和 `reuse8` 配置/输入调度，一次启动处理整个 batch，共 32 个 W1 加 4 个 W2 DMA 描述符。
- 两条路径均从 SRAM 接受 BEGIN 写入计至接受 END 写入；全部输出必须在 END 前写入相同 SRAM 地址。固件装载、启动和 END 后的 golden 自检/统计不计入。
- testbench 逐字节检查计时内的全部输出，禁止 END 前读取 golden，并验证纯 CPU 路径没有访问 NPU/DMA、HAR 描述符源地址及任务计数正确。

每种 batch 生成对应程序，因此不同 batch 的 CPU 拍数不能按样本数线性外推。以上是这套标量基准与这些固定输入的实测结果，也不能与 RAW 单层或混合图的加速比直接比较。

## NPU 与 DMA/MAC 计数

| batch | NPU 内核周期 | FC1 发射 | FC2 发射 | DMA read overlap | DMA write overlap | DMA/MAC total overlap |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 805 | 128 | 16 | 133 | 132 | 133 |
| 2 | 857 | 256 | 32 | 269 | 268 | 269 |
| 4 | 952 | 512 | 64 | 466 | 499 | 500 |

total 对读写同拍去重，不能将两项 overlap 相加。表中硬件计数与真实 START/DONE 区间核对通过。

## 边界与原功能回归

新增基准共完成 **10 次完整 SoC 仿真**：三个训练模型 batch 的 CPU/NPU 对照，以及两个单样本定向场景的 CPU/NPU 对照，全部通过 hidden、分数和类别检查。

- `seed=0, batch=1`：覆盖 W1 从 `0x80000ffc` 起始的 DMA 4 KiB 边界拆分，CPU/HAR 为 51,717 / 1,524 拍。
- `seed=5, batch=1`：覆盖 FC1 两处、FC2 一处 INT22 最终和回绕；重定标 `mult=65535, shift=31`，有六个正乘积超过 UINT32，其中三个舍入产生低 32 位进位。CPU/HAR 为 51,694 / 1,519 拍。

`firmware.build()` 仅新增可选 benchmark 和 batch 参数；默认生成的六组训练固件 HEX 与修改前逐字节相同。原 `run.py --count 32 --trained --soc` 也再次通过：41 组计算、8 组 DMA 响应协议，以及 80 组 POR / 80 组 NDM 复位检查。原完整 SoC 仍为 testbench **2700 拍** / 硬件 **2695 拍**，DMA/MAC 总重叠 **500 拍**。

原 2700/2695 拍使用启动后的完整自检区间，包含 CPU golden 检查；新 2612 拍使用成对 BEGIN/END 并写回结果，两者口径不同。原默认固件与其性能没有改变。本次改动均在测试和文档中，RTL 与 EDA 配置没有变更。

## 复现与文件

只需 Python 标准库和 ModelSim，无需 PyTorch 或 NumPy：

```bash
python test/int8/run_har_benchmark.py --vsim /path/to/vsim
python test/int8/run_har_benchmark.py --seed 0 --seed 5 --batch 1 --vsim /path/to/vsim
```

默认测 `seed=10000` 的 batch=1/2/4，可用 `--batch 4` 单独测四样本。结果、固件和日志写入本地忽略的 `test/int8/runs/har_bench_<时间戳>/`。10 ns 为功能仿真时钟周期，本报告记录周期比。

- [har_benchmark.py](../test/int8/har_benchmark.py)：生成成对 CPU/HAR 固件、输出布局和参考数据。
- [tb_har_benchmark.sv](../test/int8/tb_har_benchmark.sv)：完整 SoC 执行、BEGIN/END 计时、输出及 DMA 检查。
- [run_har_benchmark.py](../test/int8/run_har_benchmark.py)：运行对照、核对逻辑操作数、汇总周期和源码/固件哈希。
- [har_speedup.json](har_speedup.json)：本次结果、边界覆盖、六组原固件哈希及原回归记录；训练基准目录为 `har_bench_20261118_174519`，定向目录为 `har_bench_20261118_174940`，原 HAR 回归目录为 `20261118_175034`。
