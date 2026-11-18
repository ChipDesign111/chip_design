# INT22 分块 GEMV 与 CPU 多层运行时

本分支在原有 HAR 模式之外增加 RAW GEMV 模式。硬件仍使用 16 个 INT8 点积乘法器、一个原有重定标乘法器、INT22 累加器、最多四个样本、两个 64 B 权重 bank 和一块 8 KiB 主 SRAM。大矩阵的输入维、输出维和网络层数由软件分块调度，不通过扩大硬件阵列实现。

## 原有功能与新增接口

复位后的 `MODE=0` 保持原有 64→32→6 HAR 流程、数据窗口、算术契约、DMA 打包和计数定义。软件写 `MODE=1` 后，下一次 START 仅执行现有 FC1 的 32 输出×64 输入计算块，完成后直接置 DONE；不会执行重定标、FC2 或 Argmax，也不会校验或预取 W2。模式和原有配置均只能在 NPU 与 DMA 空闲时修改。

以下地址为 NPU 基址 `0x70000000` 内的字节偏移，使用对齐的 32 位访问。

| 偏移 | 方向 | 定义 |
| --- | --- | --- |
| `0x3c` | 读写 | MODE：0 为 HAR，1 为 RAW，其他写值置 ERROR；复位为 0 |
| `0x80` | 写 | RAW_INDEX：`sample*32+output`；高于 bit6 的写数据必须为零 |
| `0x84` | 读 | RAW_DATA：所选原始 INT22 累加值的 32 位符号扩展 |
| `0x88` | 读 | RAW_READY：bit0 表示所选数据已就绪，其余位为零 |

仅成功完成的 RAW 任务允许写 RAW_INDEX。样本范围依据最近一次 START 捕获的 batch 判定，完成后改写 batch 不能访问未参与计算的样本。每次合法索引写都清除 READY；原有两级重定标选择寄存器完成选择后重新置位。CPU 必须轮询 READY，不能依赖固定的 MMIO 总线延时。读取 RAW_DATA 不清除 READY；在保持 RAW 模式且无 ERROR 时，数据在下一次合法索引选择、START、ACK 或复位前保持有效。ERROR、MODE=0 或非 RAW 完成状态下 READY 和 DATA 均读零。模式设置本身不等同于 ACK，软件通过显式 ACK 或 START 管理结果生命周期。

ACK 撤销 DONE/READY；新 START 撤销旧 READY 并捕获模式和 batch；复位撤销全部有效状态。读写失败、非法索引或忙时配置写应按 STATUS.ERROR 处理，软件不得继续消费部分和。原有 STATUS.DONE/BUSY/ERROR 位定义保持不变。

RAW 仍沿用 FC1 的 bias1：

```text
raw[s][j] = wrap22(bias1[j] + sum(W[j][i] * x[s][i], i=0..63))
```

通用部分和运行时必须显式将全部 32 个 bias1 清零，尤其是 HAR→RAW 切换时不能依赖上电时的默认零值。每个 RAW 任务装载 32 个 W1 tile，共 2048 B；`loads=32`、`fc1_cycles=128*batch`、`fc2_cycles=0`。较小输入维补零，较小输出块忽略填充行。W1 布局与原实现一致：`[input_pair][output32][lane2]`。

## 软件组合方式

在 `test/int8` 目录中，可用以下 Python 接口为自己的小型网络生成完整自检镜像：

```python
from pathlib import Path
from generic_runtime import Layer
from generic_firmware import build

layers = [
    Layer([[1, -2, 3], [-4, 5, 6]], [7, -8], mult=1, shift=2, requant=True),
    Layer([[2, -3]], [9]),
]
build(Path("runs/my_model"), layers, [10, -20, 30])
```

每层权重按 `[输出][输入]` 提供，bias 为 INT32。`requant=True` 表示 ReLU 后按该层 MULT/SHIFT 舍入并饱和到 INT8；只有末层允许 `requant=False` 保留 INT32 分数。镜像内同时存放参考值用于 CPU 自检，golden 不参与计算。

离线规划位于 [generic_runtime.py](../test/int8/generic_runtime.py)。CPU 针对每层的输出维按 32、输入维按 64 分块，按需将紧凑的行优先权重打包进 SRAM 的 2048 B W1 工作区，再启动 RAW 任务。当前通用运行时使用单向量；硬件原有的四样本能力及 RAW 的 batch=1..4 不受该软件选择影响。

```text
for each layer:
    for each output block of at most 32 rows:
        CPU accumulator = layer bias
        for each input block of at most 64 elements:
            zero-pad input and pack weight tile in the SRAM working area
            execute RAW GEMV with hardware bias1 = 0
            CPU accumulator += sign_extend(raw partial sum)
        apply this layer's activation/requantization if requested
        write output for the next layer
```

bias 只加入一次，ReLU、舍入和 INT8 饱和只在该输出的全部输入块归约后执行。各输入块必须共享该输出的整数尺度；不能将各块分别饱和为 INT8 后再相加。中间层使用 ReLU 后的 0..127 激活，末层可保留有符号 INT32 分数。该版本的模型范围为全连接层及上述重定标，不声称支持任意神经网络算子。

无 bias 的 64 项 INT8 点积范围为 `[-1040384,1048576]`，位于 INT22 范围内。CPU 使用已有的 INT32 加法通路归约；离线检查拒绝可能溢出 INT32 的层。重定标的正数×UINT16 乘法、舍入与移位使用软件 64 位中间值，不增加硬件累加位宽。第一版没有接入外部存储；模型、程序、激活、部分和及工作区必须同时满足 8 KiB 布局限制，超限模型在运行前拒绝。

补零、CPU 权重打包和逐项 MMIO 读回会增加执行时间与传输量；该版本验证尺寸和层数的可组合性，不预先承诺相对纯 CPU 或原有专用 HAR 的性能优势。性能优化应依据实际计算、搬运和调度计数决定。

## 面积约束与复核方法

新增模式复用现有 `a1`、`quant_group_q` 和 `quant_value_q`。原始结果由现有组选择、8 选 1 流水串行读出，不增加一套并行累加器读口、结果阵列或乘加器。新增架构状态为顶部 MODE、一份 START 捕获的模式位和 RAW_READY，共三个控制位；实际综合可能复制或重编码控制寄存器，因此三个控制位不等于最终映射只增加三个触发器。

同样需要评估选择索引复用带来的地址选择逻辑、MMIO 译码、完成控制以及控制扇出。功能测试通过不能证明面积或物理时序保持不变。特别应分别核对 MAC 数据通路、量化选择流水及 CPU→AXI→NPU 控制路径。

本地可用 Vivado 2019.1，可用相同器件和约束对原版与新增版 `simple_npu_top` 做相对综合：

```powershell
& D:\Xilinx\Vivado\2019.1\bin\vivado.bat -mode batch -nojournal `
  -log vivado.log -source compare.tcl
```

比较必须绑定两份源码 SHA，并保持 `xc7a35tcsg324-1`、20 ns、`out_of_context` 和综合选项一致。关注 LUT、FF、DSP、RAM、层次利用率和综合时序；不能把 LUT 比例换算为 TSMC180 面积或 Density。ASIC 仍须用原有 Genus/Innovus 配置完成同条件综合和物理实现后，才能判断新的 Density、布线及时序。

本轮 Vivado 2019.1 比较已实际完成，两次综合均正常完成，批处理退出码为 0。原版基线为 `f0204e656a2d528e59c6382fe7daa62a70c2e92c`，顶层仅为 `simple_npu_top`，不含 CPU、AXI 交叉开关或主 SRAM。双方都使用上述器件、20 ns、`out_of_context` 和 `-flatten_hierarchy rebuilt`。

| NPU 综合指标 | 原版 | 新版 | 差值 |
| --- | ---: | ---: | ---: |
| Slice LUT | 11779 | 12170 | +391（+3.319%） |
| FF | 8940 | 8917 | -23 |
| DSP | 3 | 3 | 0 |
| Block RAM | 0 | 0 | 0 |
| 综合估计 Setup WNS | +6.012 ns | +5.725 ns | -0.287 ns |

这里的 DSP 是 Vivado 实际映射资源数，不是 RTL INT8 乘法器个数。FF 总数变化来自整体优化，不能用源级新增三个位直接推断。相同 SHA 的 weight store 在两个层次利用率报告中的 LUT 归属也有变化，说明该差值包含综合上下文和资源打包变化，不能将全部 +391 LUT 逐个归因于新增地址译码。综合报告存在 OOC 时钟端口 `HD.CLK_SRC` 未指定的警告，也没有布局布线，因此上述 WNS 不代表实际 FPGA 或 ASIC 时序闭合。

本轮比较脚本、独立源码快照、SHA 清单、综合报告、检查点及 `result.json` 存放在本地忽略的 `test/int8/runs/area_raw_gemv_20261118_001220/`。该目录不会随普通 Git 提交发布。面积结果绑定下列候选源码 SHA；之后若修改这两个 RTL，应重新评估，不将旧报告套到新源码。

| 文件 | 候选 SHA-256 |
| --- | --- |
| `rtl/npu/har_npu_core.sv` | `93adcc770bf449e124caad4d86fafb2360b13c65d9a5832a78706989263ef949` |
| `rtl/npu/simple_npu_top.sv` | `ed24e874deeccedba01cd013c53ef3e83f47e4d466187c0670ed2e60d3522b72` |
| `rtl/npu/har_weight_store.sv`（两版相同） | `473106074ca66f795445cd3862104d7e57da364b6ab119996eb612934b7d2913` |

原版/新版利用率报告 SHA 分别为 `a5c32b4af9dc0caa75f10b7f5b52171ec163d57219fcad5971be7bcd4a750703`、`3b32aa5258d40cc189550288093d0fdd5d94102e06780449e1edc443c8a3ff80`。本轮随后完成了全新 Genus/Innovus 01–34、同源 TT SDF 后仿和 Lab5，结果见[全流程 EDA 结果](../eda/results/fullflow_fe04981_20261118/README.md)。

## 完整SoC后仿入口

[`eda/postsim.py`](../eda/postsim.py) 会为每次已完成后端版本额外生成 `raw_tail_33x65.hex`。该场景复用已通过RTL SoC的功能fixture：33个输出、65个输入，形成4次RAW START；CPU对非整齐输出尾块和两个64输入块执行66次 `RAW_INDEX`/`RAW_DATA` 读回并完成INT32归约。综合优化可能折叠单周期MMIO请求脉冲，因此后综合测试平台检查：

- RAW模式从0进入1再回到0，且最终保持 `MODE=0`。
- 四个RAW任务对应128个W1预取，所有自动DMA源地址都位于2048 B W1工作区，不允许W2预取。
- CPU固件逐值完成66次RAW部分和读回、INT32归约和输出比较。
- 固件逐值自检完成后恢复 `MODE=0`，再执行最终异步复位。

后仿矩阵由本地 `scenarios.json` 固定身份，服务器端同时校验firmware、场景形状和输入SHA。legacy矩阵仍为16组SDF加1组unit-delay对照，新增RAW场景后总计18组。绑定物理提交 `fe04981` 的本轮 TT SDF 矩阵18/18通过；RAW场景为188032个CPU观测周期，SDF回标error、缺失实例和缺失检查均为0，全部阶段动态时序违规为0。

## 验证要求

旧 HAR 回归必须继续逐值检查 hidden、六路 score、类别、DMA 错误处理、保留区写保护和复位契约。RAW 回归需要覆盖 batch=1/2/3/4、全部输出索引、符号极值、非零 bias 的 INT22 回绕、无 W2 预取、忙时写保护、ACK/复位/失败后的失效和 HAR/RAW 切换。

组合运行时必须在真实 CV32E40P 上执行分块权重打包、RAW 调用、宽位归约及层间转换；通过向 SRAM 灌入预计算最终结果不能替代该验证。至少覆盖输入维大于 64、输出维大于 32、非整块尾部、总和超过 INT22 但仍在 INT32 内，以及三层或更多层的网络。现有 HAR 的物理归档只验证其绑定的历史源码，不能用于证明本分支的物理实现。

本轮结果和源码 SHA 见 [验证汇总](generic_validation.json)。旧 HAR 的 41 组计算、8 组 DMA、完整 SoC 及 80 POR/80 NDM 相位均通过，完整 SoC 仍为 2700/2695 拍。RAW 的 32 组用例逐值核对 2560 个结果，并覆盖连续索引→ACK/START 的流水撤销。CPU 的 260 项参考/拒绝检查和以下完整 SoC 场景全部通过：

| CPU 自检场景 | RAW 块数 | 完整周期 |
| --- | ---: | ---: |
| 33×65 非整齐矩阵 | 4 | 188031 |
| 1×129 点积，结果 2113553 超 INT22 | 3 | 136934 |
| 17→9→5→3 三层网络 | 3 | 139492 |
| 64 位重定标，含未饱和舍入进位 | 3 | 137849 |

第四例补充验证完整乘积 `65537×65535=2^32−1` 的低 32 位加舍入数产生进位，SHIFT=31 后应得 2。CPU 最终 hidden 为 `[127,0,2]`，下一层分数为 `[16008]`。初轮四例和补充第四例的清单只改变测试数据，RTL、固件生成器和运行时等 90 个源码 SHA 相同。
