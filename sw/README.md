# CPU 软件

[include/](include/README.md)、[drivers/](drivers/README.md)、[tests/](tests/README.md)、[startup/](startup/README.md)。
计划建立裸机构建与驱动：C/汇编→ELF→map/反汇编→hex→SoC。
当前 scripts/build_har_firmware.py 可生成不依赖 GCC 的 RV32I 自检：装载权重/输入/偏置、带超时轮询、逐项比较隐藏层/得分/类别、ACK 后连续运行。原四个 Lab 3 镜像在 verification/lab3/soc/。这条路径已在真实 CPU 执行，尚未建立 C 驱动工具链。
原 Lab 预编译程序不等于自主软件已有构建链。关注 [存储预算](../docs/memory-budget.md)。
