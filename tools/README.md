# 工程工具

project.py是统一入口；check_repo.py检查最终版目录/链接/地址；check_hardware.py校验课程外围；workspace.py管理独立运行记录；simulation.py运行仿真并检查通过标记；riscv_assembler.py生成真实CPU执行的RV32I程序；memory_profile.py选择主存后端。

测试和综合脚本只在test/2026-10-20/scripts；授权模型只在忽略的tools/local/vendor。当前分支没有历史驱动/兼容测试依赖。命令见 [开发说明](../report/development.md)，旧版管理见 [本地归档](../report/local_archive.md)。
