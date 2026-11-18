# 固定权重 GEMV 的软件优化

已移除固定模型在推理期间的权重重排。完整 32×64 区域由生成固件的 Python 编译器预先排列，DMA 直接读取这些权重；不完整的边缘由 CPU 计算。没有完整区域的模型直接生成纯 CPU 固件。

这采用了原 HAR 的权重准备方式。HAR 原本就把 W1/W2 预先排入固件镜像，没有首版通用 RAW 的运行时打包问题。本轮只修改软件生成和验证流程，RTL、INT22 位宽、乘法器数量和 8 KiB SRAM 均未改变。

## 实测结果

2026-11-18，在相同完整 SoC RTL 上，对七个模型各运行 CPU、动态打包 RAW、优化版，共 21 次仿真。加速比为 `纯 CPU 周期 / 优化版周期`。全部层的结果逐字节正确，所有 CPU golden 自检均在计时结束之后。

| 模型 | 纯 CPU 周期 | 原动态 RAW 周期 | 优化版周期 | 相对 CPU 加速 | 优化版路径 |
| --- | ---: | ---: | ---: | ---: | --- |
| 32×64 满块 | 45624 | 57242 | 4997 | 9.130× | 1 个 RAW 块 |
| 33×65 尾块 | 47397 | 189720 | 9199 | 5.152× | 1 个 RAW 块＋97 项 CPU 乘加 |
| 1×129，归约超 INT22 | 2832 | 133116 | 2832 | 1.000× | CPU |
| 17→9→5→3 三层 | 6074 | 134036 | 6074 | 1.000× | CPU |
| 65→3→1，64 位重定标 | 4626 | 133037 | 4626 | 1.000× | CPU |
| 65→33→5→3 混合三层 | 52606 | 279596 | 13278 | 3.962× | RAW＋CPU 边缘，后续层用 CPU |
| 32×96，长输入尾部 | 67128 | 110084 | 24600 | 2.729× | 1 个 RAW 块＋1024 项 CPU 乘加 |

小模型的 1.000× 表示编译器选择 CPU，避免原来的额外开销；不将这些模型计作 NPU 加速。当前规则只对完整 32×64 区域使用 RAW，是针对这些场景验证的分派策略，不声称对所有模型均为最优。

详细分段周期、各层分派、模型、源码和固件 SHA 见 [测量记录](gemv_optimization.json)。初次测量及慢速原因保留在 [基线报告](gemv_benchmark.md)。

## 实现方法与容量

每层拆成完整核心、右侧剩余列、底部剩余行。核心权重以 `[输出块][输入块][输入对][32 个输出][两条 lane]` 排列，后面紧接右侧权重和底部权重；两个边缘各自按行优先存储。整个变换只是排列，不加补零，不保留第二份权重。

以 33×65 为例：

| 部分 | 权重字节数 | 执行方式 |
| --- | ---: | --- |
| 前 32 行、前 64 列 | 2048 | RAW |
| 前 32 行、最后 1 列 | 32 | CPU |
| 最后 1 行、全部 65 列 | 65 | CPU |
| 总计 | 2145 | 与原紧凑矩阵相同 |

逐块补零会需要 8192 B 权重，单是权重就超出可用空间。新排列消除了该膨胀，也将这例的 NPU START 从 4 次降为 1 次。输入的完整 64 B 块使用 32 位 LW/SW 搬运。NPU bias1 在开始时清零；各层 bias 只在 CPU 初始化累加器时加入一次，全部核心和边缘归约后才进行共享的 ReLU、64 位重定标、舍入及饱和。

旧的 2048 B W1 打包工作区不再参与优化版的数据搬运，改用其开头每层 16 B 存放只读分派描述符。模型和激活仍使用原来的容量检查，固件保留 2048 B 代码区。混合程序的计时版代码实际为 1020 B；无 RAW 的模型复用 592 B 的 CPU 计时程序。均在同一 8 KiB 镜像内，不增加 SRAM。

## 使用入口

固定模型应使用新入口，模型和数值参数仍使用原来的 `Layer`：

```python
from pathlib import Path
from generic_runtime import Layer
from optimized_firmware import build

layers = [Layer([[1] * 65 for _ in range(33)], [0] * 33)]
metadata = build(Path("runs/my_fixed_model"), layers, [1] * 65)
print(metadata["layer_dispatch"])
```

普通 `build` 生成可直接加载的完整自检固件；`benchmark=True` 才生成 BEGIN/END 计时标记并把全部自检移到 END 之后。上例生成 1 次 RAW START，CPU 计算边缘，并在结束时恢复 `MODE=0`。

原 [generic_firmware.py](../test/int8/generic_firmware.py) 的默认动态打包入口保留，四组现有固件镜像逐字节不变。需要在运行时改变权重时仍可使用它。新的优化针对生成固件时已知的固定权重；模型加载及离线排列不属于一次推理计时，两个后端都从权重和输入已在 SRAM 的状态开始。

复现全部对照：

```powershell
.\.venv\Scripts\python.exe test/int8/run_gemv_benchmark.py `
  --vsim D:\modeltech64_2019.2\win64\vsim.exe
```

可用 `--backend optimized` 单独跑优化版，或重复指定 `--backend cpu --backend optimized` 只比较两条路径。原有 `run_generic_soc.py` 继续检查默认动态 RAW 的兼容性。

## 验证范围

- 七个模型、三个后端的 21 次 SoC 对照通过，包含 NPU 层切换到 CPU 层和 CPU 长尾计算。
- 56 组权重布局逐字节还原检查通过，覆盖多输入/输出完整块和各种空边缘；260 项原有整数参考与拒绝检查通过。
- 三个小模型的优化版固件与 CPU 基线的 8 KiB 镜像逐字节相同，自动分派没有推理期间的判断开销。
- 不含 BEGIN/END 的普通优化固件另外验证满块、33×65 和 CPU→RAW→CPU 三层模型，输出、自检、MODE 恢复及 DMA 范围均通过。
- 原 RAW 的 32 组、2560 个结果、故障处理、ACK/START 失效及 HAR 切换回归通过。原 HAR 完整 SoC 和复位契约的复核结果记录在上述 JSON 中。

计时边界仍为实际 SRAM BEGIN/END 接受边沿，包含初始化、DMA、MMIO、轮询、归约、输出处理和模式恢复。优化版的 CPU 权重打包周期为零；NPU 内部计数在每个 START/DONE 区间累加核对，不替代端到端周期。功能仿真的 10 ns 时钟不代表新的物理时序签核结果。

实现位于 [optimized_firmware.py](../test/int8/optimized_firmware.py)，共享 CPU 算术和自检代码，基准入口与被动监视器仍为 [run_gemv_benchmark.py](../test/int8/run_gemv_benchmark.py) 和 [tb_gemv_benchmark.sv](../test/int8/tb_gemv_benchmark.sv)。本轮本地证据位于被忽略的 `test/int8/runs/gemv_bench_20261118_143841/`，持久结果为上述 JSON。
