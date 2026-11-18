# 主 SRAM、启动和复位

主存为一个 2048×32（8 KiB）单端口 SRAM。chip_sram_2048x32 以 CHIP_USE_RA1SHD 选择授权 RA1SHD_2048x32M8 原生宏，否则使用无数据复位的行为模型。FPGA_INIT_FILE 非空仅用于 FPGA BRAM 预装载；ASIC 默认空，真实 SRAM 上电内容未知。

`my_mainmem.sv` 在系统时钟上升沿与 AXI 适配器同时接收命令，寄存地址、数据和字节写掩码；SRAM 使用反相时钟，在随后的系统下降沿执行。读结果在下一上升沿的 AXI 响应采样前返回，不增加完整 AXI 周期。反相器属于时钟路径：输入寄存器到 SRAM、SRAM 到响应接收寄存器都必须检查真实的半周期时序，不能添加异步时钟组或假路径来跳过。

`sram_transaction_reset.sv` 用两级下降沿采样把根复位限定到共享事务域，SRAM AXI 桥和 `my_mainmem` 使用同一个输出。根复位请求应保持有效并让系统时钟运行至少两个下降沿。事务复位有效时桥停止 req 和 AXI ready/valid，内存端口停止接受新请求；已捕获的 payload 不会被异步清零，仍完成一次原访问。共享复位集成回归见 [sram_transaction_reset_port.json](sram_transaction_reset_port.json)。

端口的地址、数据和字节掩码寄存器没有异步复位。复位时，已经接收的访问仍可执行一次，后续上升沿将请求有效位清零；上游 AXI 地址被异步清零时不会直接改变 SRAM 引脚。SRAM 不清空，重新启动仍需完整装载和提交。这个协议保证“停止接收新访问”，不承诺撤销已经接收的写入；复位期间系统时钟需继续运行以排空这一个访问。任意相位复位的实际电路时序仍需用本版布局后的 SDF 验证。

CPU 上电不取指。先释放外部复位，调试模块经过同步后可以工作；通过 Debug SBA 顺序写满 0x80000000–0x80001ffc 的 2048 个完整字（空白区域也写零）。建议读回校验，然后向 0x0001003c 写密钥 0xb007c0de。Boot 控制器检查覆盖计数，再经 5 拍余量才置 boot_ready，CPU 从固定跳板进入 SRAM。只写密钥、只写末字、部分字节写和半份程序都不能启动。

调试请求也能让尚未提交镜像的 CPU 离开控制器 RESET 并进入 Debug Mode，
供寄存器访问及 progbuf 装载使用。SoC 向 DM 报告
`unavailable = !(debug_running | debug_halted)`：复位后等待启动是 unavailable，
进入调试模式后是 halted；不能直接把 unavailable 接成 `!boot_ready`。
调试 AXI 桥跟随交叉开关的系统复位，避免 NDM reset 中止上游事务后留下旧的
WAIT_WVALID；DM 寄存器和 JTAG 传输保持原 POR 域。

Boot ROM 从 `0x00010000` 开始执行固定的六条 RV32I 指令：读取
`0x0001003c`、右移 13 位得到 ready、为零时回跳到读取指令，ready 为 1 后
跳到 `0x80000000`。代码占 24 B，落在既有 32 B Boot 缓存行内；状态字在该行
之外，按非缓存访问读取。提前 debug resume 因而可以运行 Boot 轮询，却不会
由这个入口进入未提交的 SRAM。显式把 DPC/恢复地址设到 SRAM 可绕过 ROM，
不属于此启动保护的范围。完整汇总见 [启动与调试修复](boot_debug_guard.md)。

POR/系统域复位异步断言、同步释放，共两组四级寄存器；所有启动许可在复位时撤销。JTAG TAP 的外部复位保留其 TCK 域接口。重新加载应先停机/系统复位，再完整装载，不能假设已经运行的 CPU 会被 fetch_enable 的下降沿立即硬复位。

测试镜像布局：0x0000–0x0fff 程序空间，0x1000–0x17ff 第一层权重，0x1800–0x18ff 第二层含填充权重，0x1900 起偏置，0x1a00 起两个输入，0x1b00 起参考结果，0x1fc0 起统计及完成标志。均为 SRAM 内偏移；不把模型和代码叠放。

Boot word14（地址 `0x00010038`）提供完整 SoC 周期计数。系统复位或重新加载
会清零计数器；`boot_ready` 置高后，CPU 在退出内部 debug halt 状态后第一次
发出指令取指时开始计数。正常启动通常首先取指 Boot 跳板 `0x00010000`，而
调试恢复也可能从保存的 DPC 直接继续。计数器不包含镜像装载、启动提交、
预装载等待、debug halt 或 JTAG resume 延迟。固件向 `0x80001FE0` 写入
PASS/FAIL 完整字后冻结；该值包含首次执行取指到自检完成的实际 SoC 周期，
也不同于 NPU 内部的 `cycle_count`。
