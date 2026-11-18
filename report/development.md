# 当前开发与验证

```powershell
python tools/project.py doctor
python tools/project.py check
python tools/project.py test --soc
```

check检查目录范式、文档链接、Python语法、硬件来源SHA和MMIO布局。test运行原41组（32随机、6训练批次、3个Argmax定向）、DMA错误/启动保护、完整SoC与复位协议、单双层FC、任务ABI、11,788组缩放向量，以及直接/缓存两种任务引擎保护回归。完整SoC需ModelSim，单元需Icarus。

使用装有compiler/requirements.txt依赖的Python执行模型验证：

```powershell
python test/int8/test_task_planner.py
python test/int8/run_model_compiler.py --soc --task-engine
python test/int8/run_task_compiler.py --soc
python test/int8/run_task_reset_soc.py --lut-cache
```

生成的CPU程序通过真实Debug SBA、AXI和SRAM装载并执行。物化张量由SBA读回，融合/内部张量按被动trace核对整数边界。复位回归覆盖POR/NDM共同边界、在途AXI事务和NPU执行中断恢复。

产物统一在忽略的test/int8/runs/下；只把复现所需的冻结输入、摘要与当前验收结果收录在report/results。CI验证开源RTL和编译器子集，不替代商业SoC、SDF或Lab5。完整EDA入口见[操作指南](../eda/README.md)。
