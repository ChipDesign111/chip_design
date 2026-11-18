# 存储和启动

my_mainmem/chip_sram_2048x32：8 KiB 主 SRAM 的可移植/原生宏后端。
sram_transaction_reset：AXI SRAM 桥与主存命令寄存器共享的下降沿事务复位边界。
bootram：固定指令轮询 ready 位的启动跳板、完整镜像覆盖检查和启动提交寄存器。
bootrom：未进入当前 filelist 的原课程常量模块，不参与实现。
ra1shd_blackbox：外部授权宏接口声明，不含工艺实现。

启动步骤和测试镜像布局见 [SRAM](../../report/sram.md)。

调试器在提交前从 `0x00010000` 恢复时，CPU 循环读取非缓存的
`0x0001003c`，仅在 bit13（ready）为 1 后跳到 `0x80000000`。
ROM 指令始终不随 ready 改变，适用于当前缓存第一条 32 B Boot 行的取指模块。
显式将调试恢复地址设为 SRAM 可绕过 ROM；这不是对调试器的访问隔离。
接线、复位域和回归说明见 [启动与调试修复](../../report/boot_debug_guard.md)。
