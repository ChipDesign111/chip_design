# Development and verification

## 环境与入口

Python 3.11+；Icarus/vvp 运行核级和 MMIO；NumPy 依赖锁在 model/requirements.txt；ModelSim 运行完整 SystemVerilog SoC；Yosys 检查通用结构。推理无需 Torch 或 checkpoint 反序列化。工具从 PATH 查找，也可使用 --iverilog / --vvp / --vsim / --yosys 指定。

```sh
python -m pip install -r model/requirements.txt
python tools/project.py doctor
python tools/project.py check
python tools/project.py test --suite unit --count 12
python tools/project.py ci
```

## 修改与验证

从更新后的 main 创建短期分支。先明确行为/通过标准，修改最小模块；新增RTL进入rtl/filelist.f，并同步相关核级和综合源列表。最终版使用test/2026-10-20/scripts/run_stream_tests.py的NEW_RTL及check_stream_synthesis.py；INT8兼容版使用test/2026-10-15/scripts/run_tests.py的HAR_RTL。两版通过CHIP_STREAM_NPU选择，具体文件与边界见 [RTL说明](../rtl/README.md)。

| 验证 | 命令（前缀 python tools/project.py） |
| --- | --- |
| 目录、链接、Python、地址、保留硬件 | check |
| 1000 合成参数组 / 3000 推理与 MMIO | test --suite unit |
| SRAM 全地址、掩码、随机与复位保持 | test --suite memory |
| 24 条真实输入 / 48 RTL 推理 | test --suite model |
| 完整 CPU，合成参数八次/六次自检 | test --suite soc --vsim /path/to/vsim |
| 完整 CPU，24 条真实模型输入 | test --suite model-soc --vsim /path/to/vsim |
| 最终W8A4核级、MMIO、DMA协议 | test --suite stream-unit |
| 最终W8A4与前一版真实RTL的完整SoC | test --suite stream --vsim /path/to/vsim |
| INT8兼容路径全部功能套件 | test --suite all --vsim /path/to/vsim |
| INT8 NPU与主SRAM/DMA通用综合 | synth |

最终版综合运行 `python test/2026-10-20/scripts/check_stream_synthesis.py --yosys /path/to/yosys`。

默认主存 portable-sram；存储或 SoC 套件可增加 --memory ra1shd，要求本地授权模型。完整 SoC 以 CPU 真实写入 c0dec0de 为通过条件；不能强制完成标志或修改参考规避失败。

## 测试记录

每次 test / ci / synth 在 test/YYYY-MM-DD/runs/时间戳 创建独立目录，包含 scripts、testbench、tools 快照，manifest.json 源文件 SHA 与开始/结束时间，results、logs、生成向量及 report.md。子进程共享该次目录，下一次命令使用新目录；本地大产物默认忽略。需要提交证据时，将精简结果与报告归入同一天的独立案例目录，注明源 revision/哈希和工具版本。

公开 CI 上传当次脚本、结果、日志和报告，不要求厂商资料。本地厂商运行的原始编译日志/数据库不公开上传。历史记录保留当时的脚本身份和路径语境，不能作为新版本验证结论。

## 全量真实数据

```sh
python tools/project.py download-data
python tools/project.py test --suite model-soc --data-root "model/data/UCI HAR Dataset" --memory ra1shd --vsim /path/to/vsim
```

全量模式比较 2947 条 RTL 输入；CPU 自检仍用六类各 4 条。模型预测与真实标签评估分类质量；hidden/score/class 与独立整数参考逐值比较实现正确性。

## 提交与交付

PR 说明问题、最终行为、影响和实测证据。文档运行 check；路径/工具变化实际运行受影响入口并在干净 checkout 复现；RTL/存储/数值变化运行完整相关回归。保留版权与组件条款；不提交 tools/local、数据下载、工具许可证、PDK 或本地数据库。

交付前固定 source/model/input SHA、通过 CI 与适用 SoC 回归并归档测试记录。目标交付另需约束、映射、STA、板级或物理签核证据。版本标签按兼容性管理，未发布变更记录在 CHANGELOG。

## DMA

新增 `test --suite dma-unit`（公开协议/入口回归）与 `test --suite dma --memory portable-sram|ra1shd --vsim /path/to/vsim`（同模型 CPU/DMA 对比）。`ci` 包含 dma-unit 和 DMA 通用综合；`all` 也包含完整 DMA 基准。见 [DMA](dma.md)。
