# 环境和共有运行入口

## 当前可用

Python 3.11+ 执行 `python scripts/check_repo.py`，检查骨架与配置。
当前尚无 RTL/CPU/FPGA/ASIC 的可运行入口，不把目录 README 当作完成实验。

## 本地配置

复制 `configs/env.example.json` 为 `configs/env.local.json`，填个人路径；本地文件被忽略。
记录操作系统、Python、仿真器、Icarus、RISC-V GCC 版本。具体安装以课程教程和官方来源为准，不要求每个人路径相同。

## 后续环境

- 单元仿真：Icarus 或课程仿真器；兼容性按实际源码检查。
- SoC：Lab 3 使用 ModelSim；CLab/后续工具采用课程正式环境。
- RISC-V：旧 Lab 可运行预编译 hex；自主 C 驱动需要自己的构建链。
- FPGA：板卡和工具待 Lab 6 正式发布。
- ASIC：仅在课程指定环境使用工艺库与商业工具，不将库上传到 GitHub 或提供给 AI。

共有脚本定位根目录、读取配置、独立创建 build/<任务>/<版本>；不同人和不同任务不能共用同一 work 数据库。
官方相对 filelist 路径导入时适配，禁止在共有脚本中写个人绝对路径或许可证地址。
