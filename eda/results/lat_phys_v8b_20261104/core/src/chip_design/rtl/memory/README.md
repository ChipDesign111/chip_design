# 存储和启动

my_mainmem/chip_sram_2048x32：8 KiB 主 SRAM 的可移植/原生宏后端。
bootram：固定跳板、完整镜像覆盖检查和启动提交寄存器。
bootrom：未进入当前 filelist 的原课程常量模块，不参与实现。
ra1shd_blackbox：外部授权宏接口声明，不含工艺实现。

启动步骤和测试镜像布局见 [SRAM](../../report/sram.md)。
