# 当前功能回归

```bash
python test/int8/run.py --count 32 --trained --soc
```

单元回归需 Icarus；--soc 另需 ModelSim（可 --vsim 指定路径）。--trained 增加固定 24 条 UCI 输入的训练模型逐值对照，无 NumPy 依赖。每次结果在本地忽略的 int8/runs/时间戳；int8/ 只保留当前 testbench、固件生成器和固定输入，旧版测试已归档工作区。

当前覆盖范围和已测结果见 [开发与验证](../report/development.md)。

原生授权 SRAM 行为模型可加 --vendor-model /本地授权路径/RA1SHD_2048x32M8.v（同时使用 --soc）。该 RTL 功能运行关闭模型 timing notifier，不作为 SDF 时序后仿。
