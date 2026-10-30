# FPGA 测试与多镜像加载

本目录提供 A7-35T 板级构建、JTAG 目标选择、镜像转换和 GDB 装载流程。
FPGA 系统时钟为 20 MHz，器件为 `xc7a35tcsg324-1`。

## 1. 两种 bitstream

不要把“CPU 运行后读取 SRAM”和“无预装载后用 JTAG 写入 SRAM”混在一起。

| 模式 | 构建链 | `SRAM_INIT_FILE` | `PREINITIALIZED` | 用途 |
|---|---|---|---:|---|
| 预装载 | `synth_1 → impl_1` | 指向一个 `.hex` 绝对路径 | 1 | 上电自动运行固定镜像 |
| 无预装载 | `synth_2 → impl_2` | 空 | 0 | 复位后通过 JTAG 装载任意镜像 |

当前 [fpga_top.sv](fpga_top.sv) 的默认参数为空，因此不显式传 generic 时生成
无预装载 bitstream。预装载流程由 `synth_1` 的 Synthesis Settings 传入固件路径。

### 无预装载配置

在 Vivado GUI：

```text
Window → Design Runs
→ synth_2 → Synthesis Settings → Options → More Options
```

填写不带引号的完整字符串：

```text
-generic SRAM_INIT_FILE=
```

不要写成：

```text
-generic SRAM_INIT_FILE=""
```

Vivado 2019.1 会把 `""` 当作两个实际字符，使 `INIT_FILE` 非空，仍然生成
自动启动的预装载 bitstream。

综合完成后检查：

```text
fpga/final_project/final_project.runs/synth_2/runme.log
```

必须包含：

```text
Parameter SRAM_INIT_FILE bound to: 0 - type: integer
Parameter PREINITIALIZED bound to: 1'b0
```

`impl_2` 必须是 `synth_2` 的 implementation run。烧录：

```text
fpga/final_project/final_project.runs/impl_2/fpga_top.bit
```

## 2. 固件镜像

`firmware/` 中包含 32 个随机/边界镜像和 6 个 UCI 四样本镜像。详细列表、
seed、batch 和 SHA 见 [firmware/README.md](firmware/README.md)。

默认镜像：

```text
firmware/int8_selftest.hex
firmware/int8_selftest.bin
```

`.hex` 是每行一个 32 位字的文本镜像；OpenOCD/GDB 的 `restore` 使用 8 KiB
小端 `.bin`。从其他 hex 生成 bin：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File fpga/prepare_jtag_image.ps1 `
  -InputHex fpga/firmware/int8_uci_01_batch4.hex `
  -OutputBin fpga/firmware/int8_uci_01_batch4.bin
```

转换器要求正好 2048 个 32 位字，并输出 8192 B。

## 3. Vivado 动态选择 JTAG 目标

`vivado_init.tcl` 会加载 `connect_fpga.tcl`，并在 Hardware Manager 加载后
包装 `open_hw_target`。Auto Connect 会动态选择名为 `xc7a35t` 的在线目标，
不会继续缓存旧的 `21051218003`。

检查钩子：

```tcl
info body open_hw_target
```

自动连接：

```tcl
har_connect_fpga
```

自动连接并烧录：

```tcl
har_program_fpga D:/path/to/fpga_top.bit
```

## 4. WSL 中的 OpenOCD

板上 JTAG 使用 FTDI `0403:6014`；`0403:6010` 是 UART/USB Serial 复合设备。
不要把 6010 当成 JTAG 适配器。

先在 Windows 查看 USB/IP 状态：

```powershell
usbipd list
```

JTAG 设备应显示为：

```text
BUSID  VID:PID    DEVICE                     STATE
2-2    0403:6014  USB Serial Converter       Attached
```

确保 Vivado Hardware Manager 已关闭，避免 Windows `hw_server` 和 WSL
OpenOCD 同时占用 JTAG。如果 6014 没有 Attached，在管理员 PowerShell 中：

```powershell
usbipd bind --busid 2-2
usbipd attach --wsl --busid 2-2
```

在 WSL 中检查：

```bash
lsusb | grep 0403:6014
```

然后启动现有 OpenOCD 配置：

```bash
sudo openocd -f cv32e40p.cfg
```

当前 RTL 已增加 cold-boot debug 支持：无预装载时，OpenOCD 的 halt request
可以让 CPU 从控制器 `RESET` 进入 debug，而不启动未装载的 SRAM。若烧录的是
修复前 bitstream，OpenOCD 会表现为 DMI 可读但 `Unable to halt`。

## 5. GDB 装载流程

以下命令适用于无预装载 bitstream。GDB 在 WSL 中运行时，文件路径必须使用
`/mnt/d/...`。

```gdb
cd /mnt/d/LiChade/PKU/major/AdvanceChip/chip_design/chip_design/fpga
source load_soc_image.gdb
soc-boot-status
```

刚复位、无预装载时应为：

```text
boot_status=0x00000000 loaded_words=0 ready=0
```

装载 canonical 镜像：

```gdb
soc-load-bin firmware/int8_selftest.bin
```

成功后：

```text
boot_status=0x00000800 loaded_words=2048 ready=0
```

提交启动：

```gdb
soc-commit-image
```

成功后：

```text
boot_status=0x00002800 loaded_words=2048 ready=1
```

重复执行 `soc-commit-image` 是安全的；若 `ready` 已经为 1，命令只报告
`image is already committed`，不会再次写提交码。

OpenOCD 为装载镜像会将 CPU 保持在 debug halt。提交后恢复运行：

```gdb
monitor resume
shell sleep 1
monitor halt
```

`monitor resume` 是给 OpenOCD 的命令，GDB 不一定同步更新自己的寄存器缓存。
因此 halt 后必须刷新寄存器，不能直接使用恢复前的 `$pc`：

```gdb
maintenance flush register-cache
info registers pc
x/3i $pc
monitor reg pc
```

`flushregs` 仍可使用，但已经是
`maintenance flush register-cache` 的弃用别名。

固件结束后 CPU 实际仍在执行 `j 0x80000470` 自循环，不会自己进入 debug
halt。`monitor halt` 用于得到稳定的调试现场。预期最终 PC 为：

```text
pc = 0x80000470

=> 0x80000470: j 0x80000470
   0x80000474: unimp
   0x80000476: unimp
```

`monitor reg pc` 从 OpenOCD 侧再次读取 PC，可用于排除 GDB 缓存不一致。
若刷新后仍显示 `0x10000`，说明 CPU 仍停在 Boot 跳板起点，不应视为本次
固件执行完成。

CPU 运行期间，GDB 默认的 abstract memory access 可能失败，例如：

```text
Cannot access memory at address 0x80001fe0
```

这不是内存损坏。执行 `monitor halt` 后再读取：

```gdb
x/1wx 0x80001FE0
```

预期：

```text
0x80001fe0: 0xc0dec0de
```

## 6. Boot 状态

读取地址：

```gdb
x/1wx 0x0001003C
```

| 值 | `loaded_words` | `ready` | 含义 |
|---:|---:|---:|---|
| `0x00000000` | 0 | 0 | 复位后等待装载 |
| `0x00000800` | 2048 | 0 | 镜像完整，等待启动密钥 |
| `0x00002800` | 2048 | 1 | 已提交并放行 CPU |

完整 SoC 周期由 bootram 硬件计数器记录：从启动提交开始，到固件写入 PASS
或 FAIL 的完整字为止。读取：

```gdb
x/1wx 0x00010038
```

或使用 GDB 命令：

```gdb
soc-full-cycles
```

该计数器不包含 JTAG 镜像装载时间，也不同于 NPU 内部的 `cycle_count`。

当前 canonical 镜像的完整 SoC 仿真结果为：

```text
硬件 SoC 周期             5111
testbench 观测窗口周期    5109
```

两者相差 2 拍，因为 testbench 在 SBI 提交写入完成并返回后才开始计数，而
硬件计数器从 bootram 接收提交写入的周期开始。板上 T08 应读取 `5111` 这一
硬件口径，不应把 5109 当作寄存器值。

### 启动提交码（“密钥”）

这里所说的“密钥”是启动提交码，不是加密密钥、密码或身份认证凭据。固定值是：

```text
0xB007C0DE
```

写入地址：

```text
0x0001003C
```

无预装载启动必须同时满足：

```text
1. 按顺序写满 0x80000000–0x80001FFC 的 2048 个完整 32 位字
2. 向 0x0001003C 写 0xB007C0DE
```

部分镜像、乱序写入或只写启动提交码都不会放行 CPU：

| 写入状态 | 对 `0x0001003C` 写入 `0xB007C0DE` 的结果 |
|---|---|
| 未装载 | `loaded_words=0, ready=0` |
| 部分装载 | `loaded_words<2048, ready=0` |
| 乱序装载 | 计数停在缺口处，`ready=0` |
| 完整按序装载 | `loaded_words=2048`，约 5 拍后 `ready=1` |

预装载 bitstream 不需要写这个值。`PREINITIALIZED=1` 会直接把镜像视为完整，
自动完成 release margin 并置 `boot_ready=1`。

向同一地址写 0 会执行 reload，清除 `loaded_words`、release margin 和
`ready`，但不会复位 CPU，也不会清空 SRAM。

该提交码是公开的协议常量，不具备保密、签名或防篡改能力。它能防止误把
未完成镜像交给 CPU，但不能阻止知道该值的调试器执行提交操作。

## 7. 更换下一个镜像

正确顺序：

```text
复位 SoC
→ soc-boot-status 应为 0
→ soc-load-bin <new-image.bin>
→ 检查 loaded_words=2048
→ soc-commit-image
→ monitor resume
→ 等待并检查 PASS
```

系统复位只清空 `bootram.loaded_words` 和 `boot_ready`，不会清空
`my_mainmem` 的 8 KiB 数据阵列。加载器总是重写完整的 2048 个字，包括
未使用区和零值，因此不依赖复位前的 SRAM 内容。

重新配置预装载 bitstream 会重新装入它的 `INIT_FILE`。重新配置无预装载
bitstream 不应被当作软件清零手段；测试流程始终要求完整 JTAG 装载。

## 8. T07 启动保护测试

每次测试前复位：

| 操作 | 预期 |
|---|---|
| 不装载，只写 `0xB007C0DE` | `ready=0`，CPU 不启动 |
| 只装载部分镜像后提交 | `loaded_words<2048`，CPU 不启动 |
| 乱序装载后提交 | 计数停在缺口处，CPU 不启动 |
| 完整装载后写错误密钥 | `loaded_words=2048, ready=0` |
| 完整装载后写正确密钥 | `ready=1`，最终 `0x80001FE0=0xC0DEC0DE` |

## 9. 常见问题

### `soc-load-bin` 报文件不存在

确认 GDB 在 WSL 中，并先执行：

```bash
ls -l /mnt/d/LiChade/PKU/major/AdvanceChip/chip_design/chip_design/fpga/firmware/int8_selftest.bin
```

也可以先 `cd` 到文件所在目录，再传相对路径。`source` 只加载命令定义，
不会自动找到镜像。

### `soc-boot-status` 读到 `0x2800`

说明当前运行的是预装载 bitstream，或已经完成过装载和提交。检查是否烧错
`impl_1`，并从 `impl_2/fpga_top.bit` 重新配置后复位。

### OpenOCD 显示 `Unable to halt`

先确认无预装载综合日志中 `PREINITIALIZED=0`。若 bitstream 来自修复前 RTL，
CPU 在 `RESET` 状态不响应 debug request；需要重新构建包含 cold-boot debug
修复的 bitstream。

### OpenOCD 找不到设备

检查 6014 是否 Attached 到 WSL，Vivado Hardware Manager 是否已关闭，以及
是否有残留 OpenOCD 进程占用 FTDI。

### 修改 GDB 脚本后行为没有变化

重新执行：

```gdb
source /mnt/d/LiChade/PKU/major/AdvanceChip/chip_design/chip_design/fpga/load_soc_image.gdb
```

已经加载的 GDB user command 不会自动更新。
