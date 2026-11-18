# 当前 RTL 前仿汇总

核对日期：2026-11-18。分支：`feat/int22-gemv-runtime`；核对基线：`920d82a`。

当前已有同 RTL 的 HAR、RAW、DMA、Boot/复位、取指单元、通用 SoC 和编译器批处理通过记录。部分独立专项仍只有历史 SoC 记录，见下表“历史专项”。本页汇总现有执行证据，不表示本次重新运行了全部测试。

## 版本与统计口径

| 项目 | 当前核对值 |
|---|---|
| RTL Git tree | `9c0272a82e9c9af8d37e3458358dcd00181992c5` |
| 硬件 | CV32E40P / AXI / DMA / 8 KiB SRAM / 16-MAC / INT22；HAR 与 RAW，最大硬件 batch=4 |
| 最新编译后端 | `295ffb0`：batch=2..4 权重复用，保留逐样本调度与容量回退 |
| 此前两笔后仿改动 | `8af0a28`、`c21176e` 修改后仿测试与说明，未修改 RTL 或前仿编译后端 |
| 本次性能补充 | 为 `perf.py` 增加源码/输入/日志 SHA 和可选 batch=3；HAR 入口允许 batch=3；计算 RTL 和编译后端保持原样 |
| 源码核对 | 主 HAR、通用 SoC、GEMV/HAR 性能、前端和批处理记录内的 86 项 RTL 源/包含文件/filelist SHA 与当前一致；取指专项的 3 项 RTL 输入与 testbench、runner 共 5 项一致 |
| 时钟与模型 | 主 SoC 功能仿真为 10 ns、行为 SRAM；本页不将 SDF、综合网表、FPGA 板测混作 RTL 前仿 |

“同 RTL”按记录中的源码 SHA 核对；绝对路径先归一化为仓库相对路径。旧固件或旧编译调度的结果会另行注明，不将其周期解释为当前默认调度。

下列 41 组、8 组、32 组、260 项、26 次、34 份等数字分别属于不同套件，部分是主套件的子项或重复执行，不能相加称为总用例数。原始 `test/int8/runs/` 目录为本地忽略数据；链接优先指向已提交的 JSON 证据和测试源码。

## 硬件功能、协议与启动

| ID | 测试 | 覆盖范围 | 现有结果 | 入口 / 证据 |
|---|---|---|---|---|
| H1 | HAR NPU＋DMA 单元 | 32 随机批次、6 训练批次（24 条 UCI 输入）、3 个末拍 Argmax 定向；INT22 回绕、舍入/饱和、tile/bank 交接、W2 预取、MMIO 合法/保留窗口、错误与重启 | **PASS，41 组**；Icarus | [run.py](../test/int8/run.py)、[tb_tiled_dma.sv](../test/int8/tb_tiled_dma.sv)；E1 |
| H2 | Boot 周期起点 | ready 后等待/debug-halt 不计时，首次固件取指后计时，捕获后冻结 | **PASS**；`pre_fetch=0, captured=23, frozen=23` | [tb_boot_cycles.sv](../test/int8/tb_boot_cycles.sv)；随 H1 执行，E1 |
| H3 | DMA 响应专项 | 即时/延迟 B、读/写错误、提前/延后 RLAST、32 字两次 burst、跨 4 KiB 拆分 | **PASS，8 组**；Icarus | [run_dma_response.py](../test/int8/run_dma_response.py)、[tb_dma_response.sv](../test/int8/tb_dma_response.sv)；H1 自动调用，E1 |
| H4 | 原 HAR 完整 SoC | Debug SBA→真实 AXI→SRAM 装载；无/部分/乱序/字节写镜像及错误提交密钥不能启动；真实 CPU 配置、推理并逐值检查 hidden/score/class | **PASS**；ModelSim；`2700 / 2695` 拍 | `run.py --count 32 --trained --soc`、[tb_soc.sv](../test/int8/tb_soc.sv)；E1 |
| H5 | 系统复位契约 | POR/NDM 相位扫描、复位传播、SRAM 事务边界及复位后重启 | **PASS，80 POR＋80 NDM** | [tb_system_reset_contract.sv](../test/int8/tb_system_reset_contract.sv)；随 H4 执行，E1 |
| H6 | RAW 硬件接口 | batch=1/2/3/4，32×64 点积、符号极值/偏置回绕；索引、READY、ACK、忙时保护、DMA 故障、索引后 ACK/START 的流水撤销、HAR↔RAW 切换、禁止 W2 DMA | **PASS，32 组、2560 个结果**；Icarus | [run_raw_gemv.py](../test/int8/run_raw_gemv.py)、[tb_raw_gemv.sv](../test/int8/tb_raw_gemv.sv)；E2 |
| H7 | 取指模块协议 | 精确非缓存地址、连续命中/行边界、AR 背压、失效与复位、AXI 错误/RLAST、别名、零字节使能、部分行与四态未知值 | **PASS，71 项**；Xcelium；2026-11-09 的该模块与当前逐字节相同 | [run_ifetch.py](../test/int8/run_ifetch.py)、[tb_ifetch.sv](../test/int8/tb_ifetch.sv)、[同源结果](optimization_20261109/ifetch/result.json) |
| H8 | **perf.py 独立性能** | 原训练权重/UCI 输入，固定合成 AXI 背压；batch=1/2/3/4；检查 hidden/score/class、INT22/16-MAC 发射数及原 testbench 的错误/重启检查 | **PASS，4 种 batch**；NPU 周期 **1394 / 1429 / 1455 / 1509**；Icarus | [perf.py](../test/int8/perf.py)、[tb_tiled_dma.sv](../test/int8/tb_tiled_dma.sv)、[perf_validation.json](perf_validation.json)；详见下文独立计时表 |

H1/H3/H6/H8 是 NPU/DMA 单元或合成 AXI 存储模型；H4 才是 CPU 执行固件的完整 SoC。H4 从 Debug SBA 请求边界装载，不等于物理 JTAG TAP 链路测试。

## 通用计算、编译器与成对性能验证

| ID | 测试 | 覆盖范围 | 现有结果与版本口径 | 入口 / 证据 |
|---|---|---|---|---|
| G1 | 通用参考与拒绝检查 | N/K 分块、INT32 安全范围、64 位重定标、非法参数、层连接与 SRAM 容量 | **PASS，260 项**；主机检查，不计为 RTL 仿真 | `run_generic_soc.py --reference-only`；[generic_validation.json](generic_validation.json) |
| G2 | 动态打包通用 SoC | 33×65、1×129 超 INT22、三层网络、64 位乘积舍入进位；真实 CPU 打包/归约/层间处理 | **PASS，4 场景＋1 次补充进位复测**；同 RTL 的原动态固件，含自检的周期见专项报告 | [run_generic_soc.py](../test/int8/run_generic_soc.py)、[tb_generic_soc.sv](../test/int8/tb_generic_soc.sv)、[通用报告](generic_gemv.md)；E3 |
| G3 | 纯 CPU／动态 RAW／预打包 RAW 对照 | 7 场景，各 3 路径；满块、双边缘、宽累加、多层、混合 CPU/RAW、32×96；检查全部输出、禁止 END 前读 golden、DMA 范围与任务数 | **PASS，21 次 SoC**；原整数 `Layer` 契约与四项展开 CPU 基准 | [run_gemv_benchmark.py](../test/int8/run_gemv_benchmark.py)、[tb_gemv_benchmark.sv](../test/int8/tb_gemv_benchmark.sv)、[gemv_optimization.json](gemv_optimization.json) |
| G4 | main 前端接入 | FX/量化、混合算子与残差/Softmax、留出输入、batch=2、INT32 大累加、CPU-only、小网络；补充跨输入/输出块矩阵 | **PASS，最初 22＋补充 4＝26 次 SoC**；`bcb0ae0` 的逐样本调度记录 | [run_raw_compiler.py](../test/int8/run_raw_compiler.py)、[前端报告](raw_frontend.md)、[raw_frontend_validation.json](raw_frontend_validation.json) |
| G5 | 当前编译器主机契约 | 同整数 CPU/RAW 参考、14 份历史整数固件 HEX、静态形状、输入不被原地修改、容量/非法模型、固定机器码换输入、批处理与回退 | **PASS，14 项测试**；当前批处理版本；不是 RTL 仿真次数 | [test_raw_compiler.py](../test/int8/test_raw_compiler.py)、[raw_batch_reuse.json](raw_batch_reuse.json) 的 `host_contracts` |
| G6 | RAW 跨样本权重复用 | batch=1/2/3/4、跨 K/N 块、右边缘/底部、多层、超 INT22 范围、零位移/正负饱和、两个留出输入、CPU-only、容量回退 | **PASS，16 组输入配置、34 份不同固件的 SoC 记录**；其中 13 份启用复用的固件均为最终对齐版本；基准镜像与最终重编译逐字节一致 | [run_raw_batch_reuse.py](../test/int8/run_raw_batch_reuse.py)、[批处理报告](raw_batch_reuse.md)、[raw_batch_reuse.json](raw_batch_reuse.json) |
| G7 | 原前端 batch=2 复测 | 原前端报告中的同一 Linear 模型，真实 CPU 与新 RAW 对照 | **PASS，2 次 SoC**；CPU `66621`，新 RAW `6737`，旧 RAW 为 `7025` | [raw_batch_reuse.json](raw_batch_reuse.json) 的 `original_frontend_batch2`；E4 |
| G8 | HAR／纯 CPU 加速比 | 原训练模型、相同输入/权重/量化规则；batch=1/2/3/4；补充 INT22 回绕、DMA 4 KiB 边界、大乘数/舍入进位 | **PASS，原 10＋补测 2＝12 次 SoC**；全部结果在 END 前写入 SRAM，自检在计时后 | [run_har_benchmark.py](../test/int8/run_har_benchmark.py)、[tb_har_benchmark.sv](../test/int8/tb_har_benchmark.sv)、[har_speedup.json](har_speedup.json)、[batch=3 补测](speedup_supplement.json) |
| G9 | 12,311 拍被动分段 | 同一份四样本 RAW 固件；仅增加 testbench PC 入口监视，核对总拍数及全部 SBA 读回 | **PASS，1 次被动重测**；性能分析，非新增功能场景 | E5；分段数字见下文 |
| G10 | RAW 批处理的 CPU 基线补测 | 跨 K/N 块、双边缘/右边缘/底部、多层、容量回退、CPU-only、宽累加、零位移及留出输入 | **PASS，11 次 CPU 完整 SoC**；每个张量与 G6 对应 RAW 的实际 SRAM 输出一致，纯 CPU 未访问 NPU | [run_raw_batch_reuse.py](../test/int8/run_raw_batch_reuse.py) 的 `--backend cpu`、[speedup_supplement.json](speedup_supplement.json) |

G4 的 26 次和 G6 的 34 份属于两轮记录，不能合称 60 个互不重复的当前默认模型。G4 中早期 `INTERRUPTED_FOR_INPUT_CAPTURE_FIX` 运行不计入通过；G6 中对齐前的新 RAW 数值不用于最终性能表。G3/G4 的原单样本/CPU 固件保留其独立整数语义，不能套用另一种量化模型的加速比。

## 主要周期结果

### 原 HAR 完整自检

| 指标 | 周期 |
|---|---:|
| testbench 完整 SoC / 硬件 SoC | **2700 / 2695** |
| NPU 内核 | **952** |
| FC1 / FC2 MAC 发射 | **512 / 64** |
| DMA read / write / total overlap | **466 / 499 / 500** |

overlap 的 total 对读写同拍去重，不能把两个分项相加。以上完整自检包含 CPU golden 检查，与下面 BEGIN/END 的成对推理计时不同。

### perf.py 独立 NPU＋DMA 计时

入口为 [perf.py](../test/int8/perf.py)，使用原训练模型 `64→32→6`、seed=10000 和固定合成 AXI 背压。本次四种 batch 均通过 hidden/score/class 及完整 testbench 检查，源码/输入/日志 SHA 见 [perf_validation.json](perf_validation.json)。

| batch | NPU 周期 | 每样本周期 | 批吞吐增益¹ | FC1 发射 | FC2 发射 | read / write overlap |
|---|---|---|---|---|---|---|
| 1 | 1394 | 1394.00 | 1.000× | 128 | 16 | 65 / 62 |
| 2 | 1429 | 714.50 | 1.951× | 256 | 32 | 138 / 133 |
| 3 | 1455 | 485.00 | 2.874× | 384 | 48 | 208 / 208 |
| 4 | 1509 | 377.25 | 3.695× | 512 | 64 | 277 / 266 |

¹ 批吞吐增益按 `batch × C(batch=1) / C(batch)` 推算，即 `batch×1394/C_batch`；这是该固定背压探针的 NPU 区间指标。计时从硬件 START 到 DONE，包含 DMA 等待，CPU 配置、输入写入和结果读回均不在区间内。它不等于 CPU 加速比，也不能替换 SoC 内 NPU 的 952 拍、推理区间的 2612 拍或完整自检的 2700 拍；这些数的存储/背压环境与计时边界不同。read/write overlap 未采集去重 total，不能相加代替 total。默认 batch=1/2/4 的结果也已复测保持一致。

### 完整加速比

以下列全 **42 条模型/输入配置记录**：整数 GEMV 7 条、前端接入与补充矩阵 13 条、批处理 16 条、HAR 6 条。其中包含兼容复测和留出输入，不能视作 42 个互不重复的模型。`gemv_benchmark.json` 的五条旧动态结果与整数表对应行一致，合并列示。

- **CPU 加速比**：`CPU 周期 / 对应 RAW 或 HAR 周期`；小于 1 表示比该 CPU 基准慢。
- **预打包收益**：`动态 RAW 周期 / 预打包 RAW 周期`。
- **跨样本复用收益**：`逐样本 RAW 周期 / 批处理 RAW 周期`。它与 CPU 加速比单独列出。
- 下表全部采用 SRAM 接受 BEGIN/END 的端到端计时，含配置、输入、DMA、轮询、归约/激活和输出写回，排除装载和 golden 自检。只有上一节 perf.py 使用独立 NPU 区间。

所有比值只比较同一行的整数权重、输入、batch、输出要求和数值规则。原整数满块用例输出 INT32，PyTorch Linear 输出重定标后的有符号 INT8；两者芯片端都执行整数运算，但不是同一个数值任务。不同 batch 的程序布局不同，CPU 周期不作线性外推。

#### 1. 原整数 GEMV：全部 7 场景、3 后端

来源：[gemv_optimization.json](gemv_optimization.json)。原动态路径在计时内打包权重，预打包路径将完整块交给 RAW、边缘交给 CPU。

| 场景 | CPU | 动态 RAW | CPU/动态 RAW | 预打包路径 | CPU/预打包 | 动态/预打包 |
|---|---|---|---|---|---|---|
| 32×64 满块，INT32 输出 | 45624 | 57242 | 0.797× | 4997 | 9.130× | 11.455× |
| 33×65 双边缘，INT32 输出 | 47397 | 189720 | 0.250× | 9199 | 5.152× | 20.624× |
| 1×129，整层结果超 INT22 | 2832 | 133116 | 0.021× | 2832 | 1.000× | 47.004× |
| 17→9→5→3 三层 | 6074 | 134036 | 0.045× | 6074 | 1.000× | 22.067× |
| 65→3→1，64 位重定标 | 4626 | 133037 | 0.035× | 4626 | 1.000× | 28.759× |
| 65→33→5→3 混合三层 | 52606 | 279596 | 0.188× | 13278 | 3.962× | 21.057× |
| 32×96 右边缘 | 67128 | 110084 | 0.610× | 24600 | 2.729× | 4.475× |

`beyond_int22`、`three_layers`、`requant_64bit` 没有完整 32×64 块，预打包路径在编译时直接回退 CPU，因此 1.000× 不代表 NPU 加速。动态路径没有跳过填充任务，低填充率及运行时打包使部分场景明显慢于 CPU。

#### 2. PyTorch 前端：全部 13 条记录

来源：[raw_frontend_validation.json](raw_frontend_validation.json)。仅原 `batch2` 行的当前 RAW 使用 [批处理复测](raw_batch_reuse.json) 中的 6737 拍，其余单样本或 CPU-only 生成程序保持原样。

| 场景 | B | CPU | 初期 RAW | 当前 RAW | CPU/初期 | CPU/当前 | 说明 |
|---|---|---|---|---|---|---|---|
| 64→32 Linear | 1 | 36953 | 3926 | 3926 | 9.412× | 9.412× | RAW＋CPU |
| 65→33 Linear，双边缘 | 1 | 38499 | 7792 | 7792 | 4.941× | 4.941× | RAW＋CPU |
| 65→33→5，Sigmoid/残差/Softmax | 1 | 56317 | 16334 | 16334 | 3.448× | 3.448× | RAW＋CPU |
| 同一混合图，留出输入 | 1 | 56316 | 16332 | 16332 | 3.448× | 3.448× | RAW＋CPU |
| 64→32，原 batch2 模型 | 2 | 66621 | 7025 | 6737 | 9.483× | 9.889× | RAW＋CPU |
| 64→32，整层累加范围超 INT22 | 1 | 33567 | 4002 | 4002 | 8.388× | 8.388× | RAW＋CPU |
| 17→9→5→3 小网络 | 1 | 5684 | 5684 | 5684 | 1.000× | 1.000× | CPU-only |
| 算术/激活/Softmax | 2 | 5062 | 5062 | 5062 | 1.000× | 1.000× | CPU-only |
| 原地 ReLU | 1 | 86 | 86 | 86 | 1.000× | 1.000× | CPU-only |
| 原整数 32×64 兼容复测 | 1 | 45624 | 4997 | 4997 | 9.130× | 9.130× | 与上表重复的兼容验证 |
| 原整数 33×65 兼容复测 | 1 | 47397 | 9199 | 9199 | 5.152× | 5.152× | 与上表重复的兼容验证 |
| 64×64，跨输出块 | 1 | 67039 | 7602 | 7602 | 8.819× | 8.819× | RAW＋CPU |
| 33×129，跨输入块和边缘 | 1 | 66326 | 10510 | 10510 | 6.311× | 6.311× | RAW＋CPU |

两条 `integer_*` 使用原整数入口，单独保留是为了验证前端接入没有改变旧固件。它们与 PyTorch 图的 signed INT8 张量边界区分。

#### 3. RAW 跨样本复用：全部 16 条输入配置

原 RAW 结果见 [raw_batch_reuse.json](raw_batch_reuse.json)；此前缺失的 **11 个 CPU 基线已经补测**，所有 SRAM 张量与原 RAW 实际读回逐值相同，见 [speedup_supplement.json](speedup_supplement.json)。两种 RAW 路径的 CPU 加速比及复用收益均列出。

| 场景 | B | CPU | 逐样本 RAW | 批处理路径 | CPU/逐样本 | CPU/批处理 | 逐样本/批处理 |
|---|---|---|---|---|---|---|---|
| 64→32 满块 | 1 | 36953 | 3926 | 3926 | 9.412× | 9.412× | 1.000× |
| 64→32 满块 | 2 | 77684 | 7912 | 6737 | 9.819× | 11.531× | 1.174× |
| 64→32 满块 | 3 | 116224 | 11469 | 9530 | 10.134× | 12.196× | 1.203× |
| 64→32 满块 | 4 | 180188 | 15919 | 12311 | 11.319× | 14.636× | 1.293× |
| 64→32，留出输入 | 4 | 180188 | 15919 | 12311 | 11.319× | 14.636× | 1.293× |
| 32×128，跨输入块 | 4 | 254069 | 22702 | 19218 | 11.191× | 13.220× | 1.181× |
| 64×64，跨输出块 | 3 | 232192 | 21967 | 18694 | 10.570× | 12.421× | 1.175× |
| 33×65，双边缘 | 4 | 187127 | 28120 | 26323 | 6.655× | 7.109× | 1.068× |
| 32×65，右边缘 | 3 | 98038 | 19384 | 16343 | 5.058× | 5.999× | 1.186× |
| 33×64，底部 | 2 | 68729 | 9463 | 9155 | 7.263× | 7.507× | 1.034× |
| 32×176，容量回退逐样本 | 4 | 344693 | 136835 | 136835 | 2.519× | 2.519× | 1.000× |
| 64→32→64，ReLU/Tanh | 2 | 189325 | 91985 | 83457 | 2.058× | 2.269× | 1.102× |
| 17→9→5，CPU-only | 4 | 21017 | 21017 | 21017 | 1.000× | 1.000× | 1.000× |
| 32×128，累加范围超 INT22 | 3 | 186705 | 17542 | 14909 | 10.643× | 12.523× | 1.177× |
| 32×64，零位移重定标 | 2 | 74396 | 7440 | 6737 | 9.999× | 11.043× | 1.104× |
| 零位移，留出/正负饱和 | 2 | 74332 | 7377 | 6675 | 10.076× | 11.136× | 1.105× |

容量回退仍可使用逐样本 RAW，不能标成 CPU-only；只有 `cpu_only_b4` 完全没有 NPU 任务。batch=1 使用原路径。基准为现有四项展开标量内核，表中不宣称 CPU 峰值性能。

#### 4. HAR：四种训练 batch 与两个定向边界

来源：[har_speedup.json](har_speedup.json)；batch=3 为本次补测，来源 [speedup_supplement.json](speedup_supplement.json)。两路均输出全部 hidden、六类分数和类别，INT22 回绕/ReLU/精确重定标/argmax 规则相同。

| seed | 场景 | B | CPU | HAR 端到端 | CPU/HAR |
|---|---|---|---|---|---|
| 10000 | 原训练模型/UCI 前缀 | 1 | 51613 | 1525 | 33.845× |
| 10000 | 原训练模型/UCI 前缀 | 2 | 76104 | 1918 | 39.679× |
| 10000 | 原训练模型/UCI 前缀 | 3 | 128162 | 2268 | 56.509× |
| 10000 | 原训练模型/UCI 前缀 | 4 | 153536 | 2612 | 58.781× |
| 0 | DMA 4 KiB 边界 | 1 | 51717 | 1524 | 33.935× |
| 5 | INT22 回绕/大乘数/舍入进位 | 1 | 51694 | 1519 | 34.032× |

HAR 与 RAW/整数图的工作负载、输出精度或 CPU 处理不同，不跨表比较加速比。HAR batch=4 的 2612 拍是成对推理区间；原完整自检的 2700/2695 拍仍保留原口径。

### 四样本 RAW 的 12,311 拍分段

| 阶段 | 周期 |
|---|---:|
| 初始配置 | 305 |
| 复制偏置、初始化 INT32 累加区 | 1847 |
| 四个样本的输入搬运 | 771 |
| 启动、NPU/DMA 执行及轮询 | 750 |
| 128 个结果读回与 INT32 归约 | **5401** |
| CPU 重定标、INT8 输出写回 | **3198** |
| 收尾 | 39 |
| 合计 | **12311** |

分段按有效译码的阶段入口划分，包含取指和总线等待。NPU busy 为 730 拍、MAC 发射为 512 拍，均已包含在上述区间内；不能额外相加。结果读回与重定标合计 8599 拍，占 69.85%。该例没有 CPU 边缘乘加。

## 历史专项与当前证据空缺

| 测试/入口 | 已有记录 | 当前归类与复测条件 |
|---|---|---|
| `run_ifetch_snoop_soc.py`：真实 SoC SRAM 写入/取指一致性 | [13 项 PASS](optimization_20261109/snoop_soc/results.json)，29 次接受写、1 次别名写、2 次零使能 | **历史通过，当前同源记录待补**。旧记录的 NPU core/top、SoC top SHA 与当前不同；取指端由 testbench 驱动，不能替代固件执行。用当前 RTL 重跑该入口 |
| `run_soc_xcelium.py --debug-cold` / `tb_debug_cold.sv` | [冷启动 Debug PASS](ifetch_20261109/debug_cold/results.json)，halt 61 拍、PC=`0x82c` | **历史通过，当前该专项记录待补**。确认无提交镜像时能进入 Debug、boot_ready 保持 0；旧 SoC SHA 不同。当前 H2 的计时暂停检查不等同于此专项 |
| `run_soc_xcelium.py` 的多 seed/工具对照 | [历史四 seed PASS](ifetch_20261109/soc_runner/results.json) | **历史工具对照**。当前完整 SoC 功能结果采用 H4/G2～G8 的 ModelSim 记录；不能引用历史 Xcelium 拍数替换当前周期 |
| `run_firmware_bench.py`：HAR 指令调度及附加程序对照 | [历史优化汇总](loop_optimization_20261109/summary.json)，含 152 次扩展对照、SRAM 写入/代码补丁程序 | **历史 SoC 性能记录**。当前默认 reuse8 已由 H4/G8 覆盖；其余调度和附加程序需新建当前源码的 benchmark，不能复用旧 elaboration |
| `run_firmware_faults.py`：hidden/score 尾项/class golden 故障注入 | [3 组预期失败通过](loop_optimization_20261109/final_faults/results.json) | **历史通过，当前该专项记录待补**。`EXPECTED_FAILURE` 表示 CPU 成功拒绝损坏结果，不是 RTL 测试失败；先生成当前同源 benchmark，再跑负向检查 |
| `run_firmware_profile.py` / `tb_soc_profile.sv` | [历史被动性能分析](loop_optimization_20261109/final_profile/results.json) | **历史固件 profile**。当前 RAW 分段采用 G9；若分析 HAR，需复制当前 benchmark 的原固件重测 |
| `run_ifetch.py --rtl OLD --expect-uncached-failure` | [旧非缓存地址负对照 PASS](ifetch_20261109/ifetch_legacy_negative/result.json) | **历史负对照**，故意使用旧 RTL，在 `0x804` 超时；当前正向结果采用 H7 的 71 项，不把负对照算作当前模块失败 |

主 SoC 记录使用行为 SRAM；`run.py --vendor-model` 支持切换本地授权宏模型。全芯片物理 JTAG TAP 链路不在以上 SBA/显式 Debug 激励的覆盖范围内；FPGA 实测和 SDF 结果另见对应专项报告。

## 复现入口

从仓库根目录运行。Icarus 需 `iverilog/vvp`；ModelSim 可传 `--vsim` 绝对路径；Xcelium 专项需要已配置 `xrun` 的环境。PyTorch 编译检查先安装 [compiler/requirements.txt](../compiler/requirements.txt)，可使用独立虚拟环境。

| 对应项 | 命令 |
|---|---|
| 仓库/源码清单检查 | `python tools/project.py check` |
| H1～H5 | `python test/int8/run.py --count 32 --trained --soc --vsim /path/to/vsim` |
| H3 单独运行 | `python test/int8/run_dma_response.py` |
| H6 | `python test/int8/run_raw_gemv.py` |
| H7 | `python test/int8/run_ifetch.py` |
| G1 | `python test/int8/run_generic_soc.py --reference-only` |
| G2 | `python test/int8/run_generic_soc.py --vsim /path/to/vsim` |
| G3 | `python test/int8/run_gemv_benchmark.py --vsim /path/to/vsim` |
| G4；使用当前默认批处理调度 | `python test/int8/run_raw_compiler.py --soc --vsim /path/to/vsim` |
| G5 | `python test/int8/test_raw_compiler.py` |
| G6 | `python test/int8/run_raw_batch_reuse.py --soc --vsim /path/to/vsim` |
| G6 加入 CPU 对照 | `python test/int8/run_raw_batch_reuse.py --soc --backend cpu --backend sequential --backend reuse --vsim /path/to/vsim` |
| G10，仅测 CPU 基线 | `python test/int8/run_raw_batch_reuse.py --soc --backend cpu --vsim /path/to/vsim` |
| G8；默认 batch=1/2/4 | `python test/int8/run_har_benchmark.py --vsim /path/to/vsim` |
| G8，batch=3 | `python test/int8/run_har_benchmark.py --batch 3 --vsim /path/to/vsim` |
| G8 定向边界 | `python test/int8/run_har_benchmark.py --seed 0 --seed 5 --batch 1 --vsim /path/to/vsim` |
| 取指真实 SoC 一致性 | `python test/int8/run_ifetch_snoop_soc.py --out test/int8/runs/snoop_new` |
| Xcelium SoC＋冷 Debug | `python test/int8/run_soc_xcelium.py --out test/int8/runs/soc_new --debug-cold` |
| HAR 固件调度对照 | `python test/int8/run_firmware_bench.py --out test/int8/runs/fw_new --mode baseline --mode reuse8` |
| HAR 故障注入 | `python test/int8/run_firmware_faults.py --benchmark test/int8/runs/fw_new --mode reuse8 --out test/int8/runs/fw_faults_new` |
| HAR 被动 profile | `python test/int8/run_firmware_profile.py --bench test/int8/runs/fw_new --out test/int8/runs/fw_profile_new --mode reuse8` |
| H8，默认 batch=1/2/4 | `python test/int8/perf.py --seed 10000` |
| H8，完整 batch=1/2/3/4 | `python test/int8/perf.py --seed 10000 --batch 1 --batch 2 --batch 3 --batch 4` |

输出目录必须为新目录。`tools/project.py test --soc` 只封装 H1～H5，CI 的 RTL job 另加 H6/G1，编译器 job 执行 G5；它们均不等于运行本表所有 SoC、性能和历史专项。

## 原始证据位置

| 编号 | 原始位置 / 可提交的索引 |
|---|---|
| E1 | `test/int8/runs/20261118_204624/`：`source_manifest.json`、`result.json`、`boot_cycles.log`、`unit.log`、`dma_response/result.json`、`soc.log`；摘要和日志 SHA 已收录于 [raw_batch_reuse.json](raw_batch_reuse.json) 的 `legacy_har` |
| E2 | `test/int8/runs/20261118_204624_raw_gemv/`：`result.json`、`simulation.log`；源码/结果索引见 [raw_batch_reuse.json](raw_batch_reuse.json) 的 `legacy_raw` |
| E3 | `test/int8/runs/generic_20261118_001841/` 和 `generic_20261118_002210/`：源码清单、各场景固件与 SoC 日志；索引见 [generic_validation.json](generic_validation.json) |
| E4 | `test/int8/runs/raw_batch_original_batch2/`；其余批处理最终执行目录与重编译镜像逐字节绑定见 [raw_batch_reuse.json](raw_batch_reuse.json) 的每项 `executed_work/current_package` |
| E5 | `test/int8/runs/raw_batch_profile_20261118_220552/`：`profile.json`、`tb_profile.sv`、`soc.log`、`actual_words.hex`；固件 SHA-256 为 `4bcb890c620ed332c112c1292721ca63c814935241fede94a342a2a5888255b1`，与批处理报告的 `full_b4/reuse` 相同 |
| perf.py | `test/int8/runs/perf_summary_all_batches/`：4 种 batch 的输入与日志；默认配置兼容复测位于 `perf_summary_default/`；已提交 [perf_validation.json](perf_validation.json) 记录源码、输入、日志 SHA 与当前 RTL tree |
| CPU/HAR 补测 | `test/int8/runs/speedup_cpu_large/`、`speedup_cpu_other/`、`har_batch3_summary/`；已提交 [speedup_supplement.json](speedup_supplement.json) 记录 11 个 CPU 基线、HAR batch=3、源码与实际输出绑定 |
| 整数性能 | [gemv_optimization.json](gemv_optimization.json)：7 模型×3 路径、260 项参考检查、源码/固件/输入哈希；原动态版本对照另见 [gemv_benchmark.json](gemv_benchmark.json) |
| 前端接入 | [raw_frontend_validation.json](raw_frontend_validation.json)：26 次 SoC 的来源、日志、实际输出及 main 前端一致性 |
| HAR 性能 | [har_speedup.json](har_speedup.json)：原 3 个训练 batch＋2 个定向场景；[speedup_supplement.json](speedup_supplement.json) 增补训练 batch=3；两路 CPU/HAR 对照及默认固件不变记录分别保留 |

本页不把后仿 18 组或扩展后的场景数计入前仿。SDF 的场景矩阵、物理提交及证据见 [后仿操作指南](../eda/docs/后仿真操作指南.md)。
