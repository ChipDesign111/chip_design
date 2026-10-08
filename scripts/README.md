# 共有工具入口

当前已实现：[check_repo.py](check_repo.py)，检查骨架、链接、项目配置和 MMIO 窗口布局。
执行：`python scripts/check_repo.py`。

已实现 check_platform.py（原字节校验）、generate_vectors.py（独立整数 gold）、build_har_firmware.py（RV32I 自检）、run_tests.py（Icarus 单元/ModelSim SoC）。import_lab3.py 为最初选择性导入入口，通常不要重新导入冻结文件。
共有脚本定位根目录，工具由 PATH/CLI 指定，产物写 build。命令见 [环境](../docs/environment.md)。C/GCC、FPGA、EDA 入口待后续实现。
