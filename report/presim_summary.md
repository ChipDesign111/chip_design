# 当前 RTL 前仿汇总

核对日期：2026-11-18。分支：`feat/int22-gemv-runtime`；核对基线：`c21176e`。

当前已有同 RTL 的 HAR、RAW、DMA、Boot/复位、取指单元、通用 SoC 和编译器批处理通过记录。部分独立专项仍只有历史 SoC 记录，见下表“历史专项”。本页汇总现有执行证据，不表示本次重新运行了全部测试。

## 版本与统计口径

| 项目 | 当前核对值 |
|---|---|
| RTL Git tree | `9c0272a82e9c9af8d37e3458358dcd00181992c5` |
| 硬件 | CV32E40P / AXI / DMA / 8 KiB SRAM / 16-MAC / INT22；HAR 与 RAW，最大硬件 batch=4 |
| 最新编译后端 | `295ffb0`：batch=2..4 权重复用，保留逐样本调度与容量回退 |
| 最新两笔代码变更 | `8af0a28`、`c21176e` 修改后仿测试与说明，未修改 RTL 或前仿编译后端 |
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

H1/H3/H6 是 NPU/DMA 单元或合成 AXI 存储模型；H4 才是 CPU 执行固件的完整 SoC。H4 从 Debug SBA 请求边界装载，不等于物理 JTAG TAP 链路测试。

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
| G8 | HAR／纯 CPU 加速比 | 原训练模型、相同输入/权重/量化规则；batch=1/2/4；补充 INT22 回绕、DMA 4 KiB 边界、大乘数/舍入进位 | **PASS，10 次 SoC**；两路均将全部 hidden/score/class 写入 SRAM 后 END，自检在计时后 | [run_har_benchmark.py](../test/int8/run_har_benchmark.py)、[tb_har_benchmark.sv](../test/int8/tb_har_benchmark.sv)、[har_speedup.json](har_speedup.json) |
| G9 | 12,311 拍被动分段 | 同一份四样本 RAW 固件；仅增加 testbench PC 入口监视，核对总拍数及全部 SBA 读回 | **PASS，1 次被动重测**；性能分析，非新增功能场景 | E5；分段数字见下文 |

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

### 同任务的端到端对照

| 模型与计时口径 | batch | CPU 周期 | 原 RAW 周期 | 新 RAW / HAR 周期 | CPU 加速比 |
|---|---:|---:|---:|---:|---:|
| 原整数 32×64，预打包 RAW | 1 | 45624 | — | 4997 | 9.130× |
| 原整数 33×65，预打包＋CPU 边缘 | 1 | 47397 | — | 9199 | 5.152× |
| PyTorch 64→32，批处理固定模型 | 1 | 36953 | 3926 | 3926 | 9.412× |
| 同上 | 2 | 77684 | 7912 | 6737 | 11.531× |
| 同上 | 3 | 116224 | 11469 | 9530 | 12.196× |
| 同上 | 4 | 180188 | 15919 | **12311** | **14.636×** |
| 原训练模型 64→32→6，HAR | 1 | 51613 | — | 1525 | 33.845× |
| 同上 | 2 | 76104 | — | 1918 | 39.679× |
| 同上 | 4 | 153536 | — | **2612** | **58.781×** |

这些加速比仅比较同一行的整数模型、输入与输出要求。计时包含 CPU 配置、输入搬运、DMA、轮询、归约/激活及输出写回；装载和 golden 自检不计入。不同 batch 的生成程序布局不同，CPU 拍数不能线性外推。更多矩阵/混合网络结果分别见 [整数优化](gemv_optimization.md)、[前端](raw_frontend.md)、[批处理](raw_batch_reuse.md)、[HAR](har_speedup.md)。

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
| `perf.py`：独立 NPU＋DMA 固定背压计时 | 本地存在多版独立计时，旧报告也有对应结果 | **未找到带当前源码 SHA 绑定的专用性能记录**。H1/H6 已覆盖功能；专用背压下的拍数应运行 `perf.py` 后另存源码清单，不能用旧 32-MAC 数字替代 |
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
| G8；默认 batch=1/2/4 | `python test/int8/run_har_benchmark.py --vsim /path/to/vsim` |
| G8 定向边界 | `python test/int8/run_har_benchmark.py --seed 0 --seed 5 --batch 1 --vsim /path/to/vsim` |
| 取指真实 SoC 一致性 | `python test/int8/run_ifetch_snoop_soc.py --out test/int8/runs/snoop_new` |
| Xcelium SoC＋冷 Debug | `python test/int8/run_soc_xcelium.py --out test/int8/runs/soc_new --debug-cold` |
| HAR 固件调度对照 | `python test/int8/run_firmware_bench.py --out test/int8/runs/fw_new --mode baseline --mode reuse8` |
| HAR 故障注入 | `python test/int8/run_firmware_faults.py --benchmark test/int8/runs/fw_new --mode reuse8 --out test/int8/runs/fw_faults_new` |
| HAR 被动 profile | `python test/int8/run_firmware_profile.py --bench test/int8/runs/fw_new --out test/int8/runs/fw_profile_new --mode reuse8` |
| 独立 NPU＋DMA 计时 | `python test/int8/perf.py --seed 10000` |

输出目录必须为新目录。`tools/project.py test --soc` 只封装 H1～H5，CI 的 RTL job 另加 H6/G1，编译器 job 执行 G5；它们均不等于运行本表所有 SoC、性能和历史专项。

## 原始证据位置

| 编号 | 原始位置 / 可提交的索引 |
|---|---|
| E1 | `test/int8/runs/20261118_204624/`：`source_manifest.json`、`result.json`、`boot_cycles.log`、`unit.log`、`dma_response/result.json`、`soc.log`；摘要和日志 SHA 已收录于 [raw_batch_reuse.json](raw_batch_reuse.json) 的 `legacy_har` |
| E2 | `test/int8/runs/20261118_204624_raw_gemv/`：`result.json`、`simulation.log`；源码/结果索引见 [raw_batch_reuse.json](raw_batch_reuse.json) 的 `legacy_raw` |
| E3 | `test/int8/runs/generic_20261118_001841/` 和 `generic_20261118_002210/`：源码清单、各场景固件与 SoC 日志；索引见 [generic_validation.json](generic_validation.json) |
| E4 | `test/int8/runs/raw_batch_original_batch2/`；其余批处理最终执行目录与重编译镜像逐字节绑定见 [raw_batch_reuse.json](raw_batch_reuse.json) 的每项 `executed_work/current_package` |
| E5 | `test/int8/runs/raw_batch_profile_20261118_220552/`：`profile.json`、`tb_profile.sv`、`soc.log`、`actual_words.hex`；固件 SHA-256 为 `4bcb890c620ed332c112c1292721ca63c814935241fede94a342a2a5888255b1`，与批处理报告的 `full_b4/reuse` 相同 |
| 整数性能 | [gemv_optimization.json](gemv_optimization.json)：7 模型×3 路径、260 项参考检查、源码/固件/输入哈希；原动态版本对照另见 [gemv_benchmark.json](gemv_benchmark.json) |
| 前端接入 | [raw_frontend_validation.json](raw_frontend_validation.json)：26 次 SoC 的来源、日志、实际输出及 main 前端一致性 |
| HAR 性能 | [har_speedup.json](har_speedup.json)：3 个训练 batch＋2 个定向场景的 CPU/HAR 对照、默认六组训练固件不变记录 |

本页不把后仿 18 组或扩展后的场景数计入前仿。SDF 的场景矩阵、物理提交及证据见 [后仿操作指南](../eda/docs/后仿真操作指南.md)。
