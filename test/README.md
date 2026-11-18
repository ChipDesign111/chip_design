# 当前功能回归

先查 [当前 RTL 前仿汇总](../report/presim_summary.md)：列出全部测试入口、覆盖范围、源码一致性、现有结果与历史专项；下述默认命令只运行其中的主 HAR 套件。

```bash
python test/int8/run.py --count 32 --trained --soc
```

单元回归需 Icarus；--soc 另需 ModelSim（可 --vsim 指定路径）。--trained 增加固定 24 条 UCI 输入的训练模型逐值对照，无 NumPy 依赖。每次运行还执行 Boot 周期起点单测，验证 ready 后的 debug-halt 时间不计入，且首次 CPU 取指后能正常冻结。每次结果在本地忽略的 int8/runs/时间戳；int8/ 只保留当前 testbench、固件生成器和固定输入，旧版测试已归档工作区。

当前覆盖范围和已测结果见 [开发与验证](../report/development.md)。

原 HAR SoC 的 PASS 行同时打印 `DMA_read_MAC_overlap`、`DMA_write_MAC_overlap` 和 `DMA_MAC_total_overlap`。total 按 `MAC 有效 && (DMA 读握手 || DMA 写握手)` 逐拍统计，读写同拍仅计一次，不是两个分项相加；testbench 会与 NPU 硬件计数器核对。`run.py --soc` 会将完整 PASS 行回显到终端，并将三个计数保存到 `result.json` 的 `soc_timing`；Xcelium 入口也保存 total 字段。

HAR 相对纯 CPU 的加速比使用独立入口，无需 PyTorch：

```bash
python test/int8/run_har_benchmark.py --vsim /path/to/vsim
```

默认对照原训练模型同一组输入的 batch=1/2/4；CPU 使用现有四项展开 RV32IM 内核，双方保持相同 INT22/重定标/argmax 语义。BEGIN/END 包含配置、输入、推理和全部输出写回 SRAM，golden 自检放在 END 后。实测加速比分别为 33.84× / 39.68× / 58.78×，完整口径和边界验证见 [HAR 加速比](../report/har_speedup.md)。

`run.py` 还固定执行三组单样本 Argmax 定向回归：最后一次 FC2 累加使第 0 类得分上升、下降或并列时，分类必须使用最终分数。默认 32 组随机加 6 组训练及这 3 组定向用例，共 41 组。

NPU MMIO 回归逐字检查样本 2..3 输入窗口的全部 32 个合法字，以及 `0x1080–0x117f` 保留区的全部 64 个字。合法写必须更新对应输入，保留区每次写必须独立置 ERROR 且不改变任何样本输入，ACK 后错误状态必须清零。

可选 RAW GEMV 模式使用独立测试，原 HAR 回归命令保持不变：

```bash
python test/int8/run_raw_gemv.py
python test/int8/run_generic_soc.py --reference-only
python test/int8/run_generic_soc.py --vsim /path/to/vsim
```

第一项用 Icarus 验证原始 INT22 结果、模式切换与协议保护；reference-only 检查分块参考、容量和数值边界；最后一项在真实 CV32E40P/AXI/8KiB SRAM 上执行 CPU 分块、归约及多层固件。接口、数值约束和容量限制见 [通用 GEMV](../report/generic_gemv.md)。

同一任务的纯 CPU / 动态 RAW / 固定权重优化版周期对照使用独立入口：

```bash
python test/int8/run_gemv_benchmark.py --vsim /path/to/vsim
```

默认覆盖 `32×64` 满块、上述四个通用场景、混合三层和 `32×96`，可用 `--case` 选择场景，或重复指定 `--backend cpu --backend optimized` 限制后端。所有后端使用相同逻辑模型、单向量和冷复位；优化版在固件生成时排列权重，完整块交给 RAW，边缘由 CPU 计算，没有完整块时直接生成 CPU 固件，不增加权重字节数。固定模型可直接使用 `optimized_firmware.build` 生成普通自检固件，默认动态 RAW 入口保留。

从 CPU 写入 BEGIN 到 END 的实际 SRAM 接受边界计时，包含初始化、运行时已有的打包、DMA、轮询、归约和层间处理，CPU 的 golden 检查都在 END 之后。纯 CPU 使用四项展开的 RV32IM 有符号 INT8 乘法及 INT32 累加，各路径复用相同精确重定标。被动监视器逐字节检查结束前的所有层输出、禁止计时区间内读取 golden，确保纯 CPU 没有访问 NPU，并逐笔验证 DMA 源范围和每个 RAW 块的 32 个描述符。日志和 `result.json` 保存分段周期、逐块累加的 NPU/DMA overlap、数据和源码 SHA；加速比为 `CPU周期/对应后端周期`，大于 1 才表示加速。结果与固定模型的使用方法见 [优化报告](../report/gemv_optimization.md)，原始慢速版本的计数保留在 [周期对照报告](../report/gemv_benchmark.md)。

PyTorch 前端使用独立依赖环境，原回归不需要 PyTorch：

```bash
python test/int8/test_raw_compiler.py
python test/int8/run_raw_compiler.py --soc --vsim /path/to/vsim
```

需先安装 [compiler/requirements.txt](../compiler/requirements.txt)。第一项验证原整数固件 SHA、相同 CPU/RAW 整数契约、INT32 归约、量化、容量和输入检查；第二项逐层 SBA 回读完整图的实际输出，并分别记录 CPU/RAW 周期。图程序的 reference 不嵌入固件。混合图、batch=2、整层超过 INT22、纯 CPU 算术以及原整数满块和尾块均在范围内，具体使用见 [编译器说明](../compiler/README.md)。

跨样本 RAW 权重复用的独立对照：

```bash
python test/int8/run_raw_batch_reuse.py --soc --vsim /path/to/vsim
```

默认比较原逐样本 RAW 与新调度，覆盖 batch=1/2/3/4、跨输入/输出块、CPU 边缘、多层激活、INT32 大累加、零位移重定标，以及容量不足时的回退。`--backend cpu --backend sequential --backend reuse` 可加入纯 CPU；相同固件只仿真一次并标明复用的结果。testbench 检查实际硬件 batch、每次任务的 `128×batch` 发射、32 个 W1 描述符及所有输出，详情见 [批处理权重复用](../report/raw_batch_reuse.md)。

`python eda/postsim.py run` 已把当前前仿的代表场景加入完整SoC SDF后仿：动态打包 `tail_33x65`、预打包 `full_32x64`／`tail_33x65`／CPU→RAW→CPU三层、CPU-only自动回退，以及 HAR 加速比的 CPU/HAR batch=4 成对固件。它要求完成34步的物理版本由当前分支RTL生成；若RTL相对物理提交未变，可复用同一网表和SDF，但仍须重跑新固件。历史HAR物理包不能代替RAW验证，也不能只凭上述RTL功能仿真宣称版后时序通过，SDF下的加速比固件测试也不重新生成性能结论。场景矩阵和判读见[后仿真操作指南](../eda/docs/后仿真操作指南.md)。

取指模块的独立协议回归使用 Xcelium：

```bash
python test/int8/run_ifetch.py
python test/int8/run_soc_xcelium.py --out test/int8/runs/soc_new --debug-cold
```

它覆盖精确非缓存地址、连续命中、缓存边界、AR 背压、填充中失效、复位、AXI 错误及 RLAST 异常。`--rtl <旧版my_ifetch.sv> --expect-uncached-failure` 可验证旧模块在 Debug 地址 `0x804` 的超时负对照。此测试使用合成 AXI 存储模型，不替代完整 SoC、JTAG TAP 或 SDF 后仿。

`run_soc_xcelium.py` 默认运行 seed 0/1/2/10000，可重复指定 `--seed`；`--firmware-dir <基线输出目录>` 复用逐字节相同的固件，适合新旧 RTL 性能对照。输出目录必须尚不存在，每次保存原始日志、源码与固件 SHA。完整 SoC 的拍数包含 CPU golden 自检；10 ns 功能仿真时钟不代表达到 100 MHz 物理时序。

原生授权 SRAM 行为模型可加 --vendor-model /本地授权路径/RA1SHD_2048x32M8.v（同时使用 --soc）。该 RTL 功能运行关闭模型 timing notifier，不作为 SDF 时序后仿。

本轮默认 `run.py` 还自动执行 8 组 DMA 响应协议测试，检查即时/延迟 B、读写错误、异常 RLAST、32 字两次突发和跨 4 KiB 拆分。取指回归扩展到 71 项，含物理地址别名、零字节使能、已发布部分行和四态未知值；真实 SoC 写入边界单独运行：

```bash
python test/int8/run_ifetch_snoop_soc.py --out test/int8/runs/snoop_new
```

`firmware_workloads.py` 可生成 `scratch_128` 或 `code_patch_alias_byte` 附加程序，随后执行完整 HAR 自检；复现命令和适用范围见 [本轮报告](../report/performance.md)。
