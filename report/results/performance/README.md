# 同整数规则的功能性能冻结

以下为完整SoC RTL实际CPU运行，包含调度、取指、SRAM及DMA；没有减掉启动或CPU交接。
每个原有模型和FC微基准的整数参考与阶段一完全一致，六个微基准的权重/输入/校准NPZ逐字节相同。
物理时序、面积、SDF和Lab5已独立完成，见[本版验收](../README.md)；本表只记录RTL测量，不替代物理证据。

| Model | Before cycles | After cycles | Change | FC starts before/after | CPU segments after | Descriptors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| mixed0 | 3724 | 2521 | -32.30% | 2/2 | 2 | 3 |
| mixed1 | 3724 | 2522 | -32.28% | 2/2 | 2 | 3 |
| cpu_only0 | 7602 | 7602 | +0.00% | 0/0 | 0 | 0 |
| wide0 | 2044 | 1042 | -49.02% | 2/2 | 1 | 2 |
| range_fallback0 | 496 | 496 | +0.00% | 0/0 | 0 | 0 |
| output_tiled0 | 1959 | 906 | -53.75% | 2/2 | 1 | 2 |
| cpu_arithmetic0 | 2961 | 2961 | +0.00% | 0/0 | 0 | 0 |
| trained_har0 | 4019 | 1727 | -57.03% | 2/2 | 1 | 2 |

## 周期分解

按每拍互斥分账：MAC核心忙时优先归其状态，其余任务忙时归任务状态，再归最近已接受CPU指令阶段。
硬件计数比上述bench观察周期少5拍，二者时间边界沿用冻结基准；下表合计为硬件计数。
CPU仍可能与NPU并行，此分账不是CPU停顿原因证明；AXI等待视图与此重叠，不能重复相加。

### mixed0

| Category | Before | After |
| --- | ---: | ---: |
| FC MAC ISSUE | 24 | 24 |
| Weight unready | 176 | 159 |
| Weight ready control | 15 | 15 |
| Task descriptor/input/bias/output DMA | 0 | 164 |
| Task quant/activation/LUT/packing | 0 | 358 |
| Internal handoff | 0 | 0 |
| Task control | 0 | 22 |
| CPU input/bias/result copies | 622 | 0 |
| CPU schedule/launch/poll tail | 113 | 106 |
| CPU quantization loop | 550 | 289 |
| CPU activation | 1070 | 434 |
| CPU elementwise | 1118 | 915 |
| CPU FC fallback | 0 | 0 |
| Legacy quant/drain/argmax | 0 | 0 |
| Boot/finish/other | 31 | 30 |

### trained_har0

| Category | Before | After |
| --- | ---: | ---: |
| FC MAC ISSUE | 144 | 144 |
| Weight unready | 703 | 679 |
| Weight ready control | 48 | 48 |
| Task descriptor/input/bias/output DMA | 0 | 142 |
| Task quant/activation/LUT/packing | 0 | 578 |
| Internal handoff | 0 | 16 |
| Task control | 0 | 20 |
| CPU input/bias/result copies | 1376 | 0 |
| CPU schedule/launch/poll tail | 101 | 62 |
| CPU quantization loop | 630 | 0 |
| CPU activation | 983 | 0 |
| CPU elementwise | 0 | 0 |
| CPU FC fallback | 0 | 0 |
| Legacy quant/drain/argmax | 0 | 0 |
| Boot/finish/other | 29 | 33 |

## 数据流量

CPU LSU有效字节与实际SRAM端口字节是两个层次，不相加。SRAM端口读包括指令和重复读，写按BE计数；
DMA按两端分别列出，输出方向的R来自NPU而非主SRAM。描述符、输入、bias、LUT也是实际开销。

| Model | CPU SRAM R/W before | CPU SRAM R/W after | SRAM port R/W before | SRAM port R/W after | DMA SRAM R after | DMA NPU R after | DMA SRAM W effective after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mixed0 | 229/84 | 93/43 | 5568/84 | 3872/72 | 724 | 32 | 29 |
| mixed1 | 229/84 | 93/43 | 5568/84 | 3868/72 | 720 | 32 | 29 |
| cpu_only0 | 725/84 | 725/84 | 8736/84 | 8736/84 | 0 | 0 | 0 |
| wide0 | 208/40 | 0/4 | 2396/40 | 1748/22 | 1428 | 24 | 18 |
| range_fallback0 | 39/10 | 39/10 | 856/10 | 856/10 | 0 | 0 | 0 |
| output_tiled0 | 188/45 | 0/4 | 1596/45 | 1116/45 | 796 | 44 | 41 |
| cpu_arithmetic0 | 154/60 | 154/60 | 4760/60 | 4760/60 | 0 | 0 | 0 |
| trained_har0 | 280/74 | 0/4 | 5624/74 | 2968/10 | 2648 | 8 | 6 |

### DMA任务组成

| Model | Weights R | Descriptors R | Input R | Bias R | LUT R | Packed output R / effective W |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| mixed0 | 384 | 192 | 44 | 68 | 36 | 32/29 |
| mixed1 | 384 | 192 | 44 | 68 | 32 | 32/29 |
| cpu_only0 | 0 | 0 | 0 | 0 | 0 | 0/0 |
| wide0 | 1056 | 128 | 136 | 36 | 72 | 24/18 |
| range_fallback0 | 0 | 0 | 0 | 0 | 0 | 0/0 |
| output_tiled0 | 480 | 128 | 24 | 164 | 0 | 44/41 |
| cpu_arithmetic0 | 0 | 0 | 0 | 0 | 0 | 0/0 |
| trained_har0 | 2304 | 128 | 64 | 152 | 0 | 8/6 |

### 逐张量交接

以下是SRAM命令覆盖每个逻辑张量的次数与字节。字节排除stride padding；一次字节load可能导致整个32位字重复读取。
它同时覆盖CPU和DMA对该张量的SRAM访问；内部/融合张量的新值由被动整数trace验证。

#### mixed0

| Tensor | SRAM read commands before/after | SRAM write commands before/after | Covered R bytes before/after | Covered W bytes before/after |
| --- | ---: | ---: | ---: | ---: |
| add | 3/3 | 12/12 | 12/12 | 12/12 |
| add_1 | 15/15 | 5/5 | 51/51 | 5/5 |
| fc1 | 12/0 | 12/0 | 48/0 | 12/0 |
| fc2 | 5/5 | 5/2 | 17/17 | 5/5 |
| mul | 12/12 | 12/12 | 48/48 | 12/12 |
| mul_1 | 5/5 | 5/5 | 17/17 | 5/5 |
| relu | 36/27 | 12/3 | 144/108 | 12/12 |
| sigmoid | 12/12 | 12/3 | 48/48 | 12/12 |
| softmax | 0/0 | 5/5 | 0/0 | 5/5 |
| x | 5/5 | 0/0 | 17/17 | 0/0 |

#### trained_har0

| Tensor | SRAM read commands before/after | SRAM write commands before/after | Covered R bytes before/after | Covered W bytes before/after |
| --- | ---: | ---: | ---: | ---: |
| _0 | 32/0 | 32/0 | 128/0 | 32/0 |
| _1 | 8/0 | 32/0 | 32/0 | 32/0 |
| _2 | 0/0 | 6/2 | 0/0 | 6/6 |
| input_1 | 16/16 | 0/0 | 64/64 | 0/0 |

## 小FC启动开销

| Shape | Requested / actual | Before | After | Change |
| --- | --- | ---: | ---: | ---: |
| k1_n1_b1 | auto / CPU | 175 | 105 | -40.00% |
| k1_n1_b1 | cpu / CPU | 105 | 105 | +0.00% |
| k7_n5_b1 | auto / NPU | 392 | 269 | -31.38% |
| k7_n5_b1 | cpu / CPU | 810 | 810 | +0.00% |
| k9_n10_b1 | auto / NPU | 614 | 357 | -41.86% |
| k9_n10_b1 | cpu / CPU | 1885 | 1885 | +0.00% |
| k16_n8_b1 | auto / NPU | 567 | 343 | -39.51% |
| k16_n8_b1 | cpu / CPU | 2415 | 2415 | +0.00% |
| k48_n24_b1 | auto / NPU | 1582 | 907 | -42.67% |
| k48_n24_b1 | cpu / CPU | 19422 | 19422 | +0.00% |
| k64_n32_b4 | auto / NPU | 5987 | 2461 | -58.89% |
| k64_n32_b4 | cpu / CPU | 136404 | 136404 | +0.00% |

1→1自动选CPU；微基准的无探针对照确认被动监控不改变该程序的周期/硬件计数。
原专用四样本2700拍是另一个独立程序，不能用这些不同batch或INT8输出的网络代替其验收。

## 新覆盖模型

| Configuration | Cycles | CPU segments | Descriptors | MODE0 segments |
| --- | ---: | ---: | ---: | ---: |
| chain | 1803 | 1 | 2 | 0 |
| chain_materialized | 2141 | 1 | 3 | 0 |
| deep | 1469 | 1 | 3 | 0 |
| split | 2706 | 1 | 5 | 0 |
| act_none | 721 | 1 | 1 | 0 |
| act_relu | 721 | 1 | 1 | 0 |
| act_relu6 | 721 | 1 | 1 | 0 |
| act_leaky | 721 | 1 | 1 | 0 |
| act_sigmoid | 749 | 1 | 1 | 0 |
| act_tanh | 745 | 1 | 1 | 0 |
| special | 3182 | 0 | 0 | 1 |
| same_shape_wrong_activation | 3616 | 1 | 2 | 0 |
| special_disabled | 3616 | 1 | 2 | 0 |
| large_cpu_fallback | 330899 | 0 | 0 | 0 |

大CPU回退模型256→20、batch4完整运行330899拍；代码、数据和权重仍在8KiB内。
新激活的CPU参考内核和原软件MMIO对照不等同于声称旧编译器已经支持所有新算子。

