# 当前功能回归

```bash
python test/int8/run.py --count 32 --trained --soc
```

单元回归需 Icarus；--soc 另需 ModelSim（可 --vsim 指定路径）。--trained 增加固定 24 条 UCI 输入的训练模型逐值对照，无 NumPy 依赖。每次运行还执行 Boot 周期起点单测，验证 ready 后的 debug-halt 时间不计入，且首次 CPU 取指后能正常冻结。每次结果在本地忽略的 int8/runs/时间戳；int8/ 只保留当前 testbench、固件生成器和固定输入，旧版测试已归档工作区。

当前覆盖范围和已测结果见 [开发与验证](../report/development.md)。

`run.py` 还固定执行三组单样本 Argmax 定向回归：最后一次 FC2 累加使第 0 类得分上升、下降或并列时，分类必须使用最终分数。默认 32 组随机加 6 组训练及这 3 组定向用例，共 41 组。

NPU MMIO 回归逐字检查样本 2..3 输入窗口的全部 32 个合法字，以及 `0x1080–0x117f` 保留区的全部 64 个字。合法写必须更新对应输入，保留区每次写必须独立置 ERROR 且不改变任何样本输入，ACK 后错误状态必须清零。

可选 RAW GEMV 模式使用独立测试，原 HAR 回归命令保持不变：

```bash
python test/int8/run_raw_gemv.py
python test/int8/run_generic_soc.py --reference-only
python test/int8/run_generic_soc.py --vsim /path/to/vsim
```

第一项用 Icarus 验证原始 INT22 结果、模式切换与协议保护；reference-only 检查分块参考、容量和数值边界；最后一项在真实 CV32E40P/AXI/8KiB SRAM 上执行 CPU 分块、归约及多层固件。接口、数值约束和容量限制见 [通用 GEMV](../report/generic_gemv.md)。

`python eda/postsim.py run` 已把 `tail_33x65` 加入完整SoC SDF后仿，作为独立的 CPU→AXI→NPU RAW场景。它要求完成34步的物理版本由当前分支RTL生成；历史HAR物理包不能代替，也不能只凭上述RTL功能仿真宣称版后时序通过。场景矩阵和判读见[后仿真操作指南](../eda/docs/后仿真操作指南.md)。

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
