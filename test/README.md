# 当前功能回归

```bash
python test/int8/run.py --count 32 --trained --soc
```

单元回归需 Icarus；--soc 另需 ModelSim（可 --vsim 指定路径）。--trained 增加固定 24 条 UCI 输入的训练模型逐值对照，无 NumPy 依赖。每次运行还执行 Boot 周期起点单测，验证 ready 后的 debug-halt 时间不计入，且首次 CPU 取指后能正常冻结。每次结果在本地忽略的 int8/runs/时间戳；int8/ 只保留当前 testbench、固件生成器和固定输入，旧版测试已归档工作区。

当前覆盖范围和已测结果见 [开发与验证](../report/development.md)。

`run.py` 还固定执行三组单样本 Argmax 定向回归：最后一次 FC2 累加使第 0 类得分上升、下降或并列时，分类必须使用最终分数。默认 32 组随机加 6 组训练及这 3 组定向用例，共 41 组。

取指模块的独立协议回归使用 Xcelium：

```bash
python test/int8/run_ifetch.py
python test/int8/run_soc_xcelium.py --out test/int8/runs/soc_new --debug-cold
```

它覆盖精确非缓存地址、连续命中、缓存边界、AR 背压、填充中失效、复位、AXI 错误及 RLAST 异常。`--rtl <旧版my_ifetch.sv> --expect-uncached-failure` 可验证旧模块在 Debug 地址 `0x804` 的超时负对照。此测试使用合成 AXI 存储模型，不替代完整 SoC、JTAG TAP 或 SDF 后仿。

`run_soc_xcelium.py` 默认运行 seed 0/1/2/10000，可重复指定 `--seed`；`--firmware-dir <基线输出目录>` 复用逐字节相同的固件，适合新旧 RTL 性能对照。输出目录必须尚不存在，每次保存原始日志、源码与固件 SHA。完整 SoC 的拍数包含 CPU golden 自检；10 ns 功能仿真时钟不代表达到 100 MHz 物理时序。

原生授权 SRAM 行为模型可加 --vendor-model /本地授权路径/RA1SHD_2048x32M8.v（同时使用 --soc）。该 RTL 功能运行关闭模型 timing notifier，不作为 SDF 时序后仿。
