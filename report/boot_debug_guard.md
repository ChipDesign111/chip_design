# 不修改 CPU 的启动与调试修复

2026-11-19，修改基线 `95dcfc8`。只修改 SoC 接线及 Boot ROM；CPU、Debug
Module、JTAG、NPU 和取指模块的实现均保持原源码。验证记录见
[boot_debug_guard.json](boot_debug_guard.json)。

## 问题与改动

CPU 复位后等待 fetch_enable 时，`debug_running_o` 和 `debug_halted_o` 都为 0。
原 SoC 把 DM 的 unavailable 固定为 0，DM 因而把该状态报告成 running。
用户当前的 OpenOCD `10b7a647d` 在 examine 初始化时，先 halt 做检查，再在
初始状态为 running 时恢复运行。这个误报会让尚未提交固件的 CPU 被恢复，
旧 Boot 两条指令又会无条件跳到保留 SRAM，最终执行旧固件。

`my_soc_top.sv` 现在连接 CPU 原有的 debug_running 输出，令
`unavailable_i = !(debug_running | debug_halted)`。等待启动报告 unavailable，
冷 halt 后报告 halted，并保持寄存器和 progbuf 可访问。fetch_enable 仍允许
debug request 唤醒 CPU，装载程序无需修改 CPU 接口。

同一次真实 JTAG 回归发现，NDM reset 中止 AXI 交叉开关事务时，原本仅随 POR
复位的 `i_dm_axi2mem` 可能留在 WAIT_WVALID。CPU 随后虽然进入 Debug Mode，
取指却停在 `0x800`，抽象命令一直 busy。该 AXI 桥现在随交叉开关一起使用
`ndmreset_n`；DM 和 DMI 本身仍使用 POR，不因系统复位丢失调试控制寄存器。

`bootram.sv` 用固定指令读取既有提交状态，ready 为零就条件回跳：

```asm
0x00010000: lui  t0, 0x10
wait_ready:
0x00010004: lw   t1, 0x3c(t0)
0x00010008: srli t1, t1, 13
0x0001000c: beq  t1, zero, wait_ready
0x00010010: lui  t0, 0x80000
0x00010014: jalr zero, 0(t0)
```

状态字 [31:14] 固定为零，bit13 为 ready，低 12 位为 loaded_words，bit12
保留为零。因此右移 13 位后得到 0 或 1，不会误把完整装载计数 2048 当成 ready。
总共 24 B，仍在现有首条 32 B Boot 缓存行内；`0x1003c` 在该行之外，真实
ready 每次通过非缓存数据读获得。不能用“ready 不同就返回不同指令”的写法，
否则取指缓存可能保留旧分支并在提交后仍不放行。

## 行为与边界

按键复位会清除启动许可及装载计数，但保留 SRAM。松开后没有调试请求就留在
RESET/unavailable；OpenOCD 发出 halt 时进入 Debug Mode/halted。若复位前
OpenOCD 已认为 CPU halted，它检测复位后可自动重新请求 halt。

从 Boot 入口提前 resume 后，CPU 正常执行 ROM 轮询，状态会变为 running，
但未进入用户 SRAM。装载齐全但尚未提交、错误密钥、不完整及乱序/部分字节写
均不能放行。完整装载并提交后，轮询自行退出，无需修改或失效 Boot 缓存行。
普通提交后 halt/resume 继续使用 DPC，保留原调试行为；预装载 FPGA 仍自动启动。

此方案保护经 Boot 入口的启动流程。调试器若显式把 DPC/恢复地址设成 SRAM
地址，或停在放行分支之后再撤销 ready，ROM 无法拦截；它不是内存访问防火墙。
因此换固件仍须先复位、halt、重装、提交，再从 `0x10000` 恢复。此修改没有
加入 CPU 端 DRET 限制，也没有硬件隔离调试器。

## 验证方法

独立入口：

```powershell
.venv/Scripts/python.exe test/int8/run_boot_debug.py --out test/int8/runs/boot_debug_NEW --vsim D:/modeltech64_2019.2/win64/vsim.exe
.venv/Scripts/python.exe test/int8/run.py --count 32 --trained --soc --vsim D:/modeltech64_2019.2/win64/vsim.exe
```

主测试 `tb_boot_debug` 使用真实 JTAG TAP、DMI CDC、DM CSR、抽象寄存器命令
和 Debug ROM，通过实际 haltreq/resumereq 完成控制。只在大镜像写入时驱动
原有 SBA 主端边界；没有 force CPU、调试请求、恢复请求、DM 状态或 SRAM 数组。
另行保留的旧 `tb_debug_cold` 兼容检查沿用原来的 force 请求方式。
不运行 OpenOCD 进程，初始化和复位恢复动作按用户当前版本源码建模。

测试将“立即写 PASS”的旧程序保留在 SRAM，再按键复位清空装载计数。监视器
禁止未就绪时的非 debug SRAM 取指和 PASS 写入；同时要求看到多次真实状态读，
防止“只是碰巧不执行”或缓存旧指令形成死循环被误判通过。覆盖：

1. 保留旧 SRAM 后复位，DM 正确报告 unavailable。
2. 冷 halt、清除 haltreq 后仍保持 Debug Mode。
3. ready=0 时，progbuf 实际写 SRAM 再读取比较。
4. 提前 resume 后，重复读取 ready，SoC 周期计数保持为零。
5. 单独提交密钥、乱序写、部分字节写无法放行。
6. 缺最后一字及完整镜像未提交/错误密钥均无法放行。
7. 正确提交使缓存中的 Boot 轮询退出，真实 SRAM 程序写 PASS 并捕获周期。
8. 提交后 DPC 读写及普通 resume 保持原行为。
9. NDM reset-halt 后读取 DPC，再提前 resume 回到受保护 Boot。
10. 按键复位后按 OpenOCD 既有 halted 状态重新 halt，不执行旧程序。

还运行两次预装载启动和原 `tb_debug_cold`。同一测试分别换回旧状态接线、旧
Boot ROM、旧 DM AXI 桥复位接线，要求在对应检查处失败，避免测试无条件通过。
默认完整功能入口也自动执行此专项，公共复位相位扫描包含调试 AXI 桥的复位域。

原有 HAR/RAW/CPU 固件在新 RTL 上重新验证，镜像及 GDB 检查内容逐字节核对，
更新来源哈希与验证记录。Boot 指令增加会改变完整 SoC 启动周期；BEGIN/END
之间的应用性能与 NPU 计数单独比较，不能直接沿用旧完整启动周期。

## 本轮结果

| 检查 | 结果 |
|---|---|
| 真实 JTAG/DMI 启动与调试 | 10 项 PASS |
| 预装载启动 | 两次复位后均 PASS |
| 原 cold-halt | PASS，61 拍进入并确认 halt |
| 旧状态接线／旧 ROM／旧桥复位接线 | 三组均在指定检查处失败 |
| HAR NPU/DMA 单元 | 41 组 PASS，含 24 条训练输入及三组 Argmax 定向 |
| DMA 响应专项 | 8 组 PASS |
| 系统复位相位 | 80 POR＋80 NDM PASS，包含调试 AXI 桥 |
| 实际 FPGA 固件 | 38 HAR＋8 HAR 配对＋16 RAW/CPU 图包，62/62 PASS |
| RAW/CPU 图张量 | 全部 SBA 回读与 reference 一致，且输出文件 SHA 与修复前一致 |
| 固件兼容性 | 207 个镜像、指令清单和 GDB 检查文件逐字节不变；生成元数据只更新来源哈希 |
| 仓库检查 | 文档链接、Python 语法、MMIO 和 75 个硬件文件哈希 PASS |

| 测量口径 | 修复前 | 修复后 |
|---|---:|---:|
| 默认 HAR 完整硬件 SoC | 2695 | 2701 |
| 默认 HAR testbench 观测 | 2700 | 2706 |
| 默认 HAR NPU | 952 | 952 |
| FC1 / FC2 发射 | 512 / 64 | 512 / 64 |
| DMA/MAC read / write / total overlap | 466 / 499 / 500 | 466 / 499 / 500 |
| HAR batch4 NPU 的 BEGIN/END | 2612 | 2612 |
| RAW full batch4 的 BEGIN/END | 12311 | 12311 |

46 份 HAR 镜像的完整硬件计数均比原来增加 6 拍，来自启动检查。
24 份成对包的应用计数及 NPU/DMA 指标逐项与修复前一致；其中 16 份图包
全部实际张量的序列化文件 SHA 也一致。完整记录见
[固件验证](../fpga/firmware/validation.json) 和 [本轮记录](boot_debug_guard.json)。

本次属于 RTL 功能验证，尚未生成此修复的新 bitstream，也未执行 EDA/SDF 或板测。
使用 FPGA 时必须重新生成并烧录 bitstream；历史物理密度、时序和板级 PASS 不构成
这两处新 RTL 的物理验证。
