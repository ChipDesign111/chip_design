# INT8 CPU/NPU SoC

当前main提供PyTorch模型编译、CPU/NPU混合执行和顺序任务NPU。硬件为CV32E40P、AXI、JTAG Debug、8 KiB SRAM、128 B取指缓存和共享16 MAC。原始64→32→6专用程序保持2700拍。

| 目录 | 当前内容 |
| --- | --- |
| [rtl](rtl/README.md) | 完整SoC及统一filelist |
| [compiler](compiler/README.md) | 模型导入、量化、K/N分块、任务表、CPU内核和RV32IM镜像生成 |
| [model](model/README.md) | 原训练模型及generic_mixed固定网络/数据 |
| [test](test/README.md) | 当前功能、保护和完整SoC回归 |
| [eda](eda/README.md) | 综合、34步实现、TT后仿、SRAM STA和Lab5工具 |
| [report](report/README.md) | 当前设计说明、冻结对照和本版验收结果 |
| [tools](tools/README.md) | 工程检查与正式辅助工具 |
| [fpga](fpga/README.md) | 板级构建及装载入口；本版未重新上板 |

```powershell
python tools/project.py check
python tools/project.py test --soc
```

模型部署从[编译器使用说明](compiler/README.md)开始。默认使用任务引擎自动搬运、量化/激活和写回；`--legacy-npu`保留兼容MMIO路径。未注册CPU内核的算子会明确拒绝。

本版已完成34步实现、23例TT SDF＋1例功能对照、同DB SRAM STA及Lab5。综合面积2.241754mm²，密度83.533%，Setup/Hold +0.070/+0.001ns。DRC/ERC按既有课程例外处理，ERC Clean=false；尚非完整流片签核。[验收结果](report/results/README.md)。

main文件树只展示当前实现、当前说明及本版对照。历次EDA、旧性能报告和板测镜像见[历史入口](report/history.md)，不混用旧版数字证明当前实现。第三方来源与许可见[组件声明](report/THIRD_PARTY_NOTICES.md)。
