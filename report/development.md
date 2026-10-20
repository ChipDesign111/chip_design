# 最终版开发与验证

Python3.11+，依赖 `model/requirements.txt`；Icarus/vvp运行核级和SRAM，ModelSim运行完整SoC，Yosys检查通用结构。各工具可用同名 `--iverilog / --vvp / --vsim / --yosys` 参数指定路径。

```sh
python tools/project.py doctor
python tools/project.py check
python tools/project.py test --suite unit
python tools/project.py test --suite memory
python tools/project.py test --suite soc --vsim /path/to/vsim
python tools/project.py test --suite all --memory ra1shd --vsim /path/to/vsim
python tools/project.py synth --yosys /path/to/yosys
python tools/project.py ci
```

unit含当前NPU逐值、248项DMA协议和异常恢复；添加 `--data-root "model/data/UCI HAR Dataset"` 运行全部2947条。soc只构建最终版，用真实CPU自检24条固定输入；不从Git历史导出另一版。ci运行公开工具可完成的check/unit/memory/synth，不要求ModelSim或厂商模型。

改RTL必须同步filelist和对应核级/综合源列表；改MMIO/数值需同步规格、固件、整数参考和金标准。改NPU/DMA跑unit、全模型、soc及synth；改主存还需双后端memory/soc。保留外围变更在manifest中说明并更新校验，不能直接删除检查规避问题。

每轮运行保存独立快照和源SHA。只有实际通过的精简证据进入validation.json，其余日志/数据库在忽略的runs。完整SoC通过标志必须由真实CPU写入。训练与旧版复测材料按 [本地归档](local_archive.md) 管理；当前分支不包含兼容设计。
