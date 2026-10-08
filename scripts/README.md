# 共有工具入口

当前已实现：[check_repo.py](check_repo.py)，检查骨架、链接、项目配置和 MMIO 窗口布局。
执行：`python scripts/check_repo.py`。

后续按任务加入：平台回归、HAR NPU 仿真、SoC 仿真、软件构建、ELF→hex、向量导出和 CLab 入口。
共有脚本自行定位根目录、读取本地配置、写入 build。不能提交个人机器路径。
当前没有 run_har 或 EDA 命令，待源码和课程工具确认后实现。
