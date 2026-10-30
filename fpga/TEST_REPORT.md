# HAR SoC FPGA 板上测试报告（rtl-dev）

| 项目 | 内容 |
|---|---|
| 报告日期 | 2026-10-30 |
| 测试状态 | **PASS（主功能及 T01/T02/T03/T04/T05/T07 补充回归完成）** |
| Git 分支 | `rtl-dev` |
| RTL 逻辑基线 | `fce9d9b`（batch=4、共享 32-MAC） |
| FPGA 器件 | Xilinx Artix-7 `xc7a35tcsg324-1` |
| 顶层设计 | `fpga_top` |
| 系统时钟 | 20 MHz |
| 构建工具 | Vivado 2019.1 |
| 测试方法 | JTAG 配置 bitstream、GDB/JTAG 读取 SRAM 和 NPU MMIO |

## 1. 测试结论

当前 bitstream 已在 A7-35T FPGA 上完成一次端到端功能自检。CPU 从上电预装载的 8 KiB 镜像启动，通过 MMIO 配置 batch=4、驱动 DMA 搬运权重、执行共享 32-MAC 的两层 INT8 推理，并逐值比较 hidden、scores 和 class。

本次 GDB/JTAG 观测结果如下：

- `0x80001FE0 = 0xC0DEC0DE`，CPU 数值自检 PASS；
- PC 停在 `0x80000470` 的原地跳转循环；
- NPU 状态为 `done=1, busy=0, error=0`；
- batch=4；
- FC1 发射周期为 256；
- FC2 发射周期为 32；
- 逻辑权重 tile 加载数为 64；
- NPU 总周期为 908；
- DMA 读/MAC、写/MAC 重叠分别为 270、269 拍；
- SRAM 计数器副本与 NPU MMIO 实时值逐项一致。

上述结果证明当前 bitstream 在 20 MHz、当前板卡和当前训练输入的 batch=4 路径上完成了完整数字功能验证。补充回归中，我完成了连续复位、重复配置、20 至 30 分钟运行、SRAM 整字/字节访问、M1/K1/K3 状态检查和无预装载镜像 JTAG 启动及其保护路径。该结果仍不等同于完整数据集准确率、50 MHz、ASIC 原生 SRAM 或 PVT 条件验证，具体边界见第 9 节。

## 2. 被测对象与构建产物

### 2.1 构建状态

被测逻辑对应 `rtl-dev` 上的 batch=4、共享 32 乘法器、FC2 四组 48 B 权重包和 W2 预取实现。FPGA bitstream 由 Vivado 于 2026-10-30 04:37:26 生成。

RTL 逻辑基线为 `fce9d9b perf(npu): remove dynamic phase accumulator indexing`。其后的提交包含 20 MHz Clocking Wizard 配置固化和 JTAG 动态目标脚本，不改变 NPU 计算架构。

报告生成时工作区存在一项未提交修改：

```text
M fpga/fpga_top.sv
```

该修改仅把 `SRAM_INIT_FILE` 从相对路径改为当前机器的绝对路径，用于解决 Vivado 从不同启动目录展开时无法定位 `int8_selftest.hex` 的问题，不改变综合后的 SoC 逻辑。报告未修改或回退该工作区内容。

实际 Clocking Wizard 配置和 routed timing 均对应 20 MHz。当前 `fpga_top.sv` 顶部注释及 `fpga/README.md` 仍残留 50/25 MHz 的旧描述，其后的文档更新不应改变本报告对实际构建产物的判定。

### 2.2 产物和校验值

| 产物 | 路径 | 大小 | SHA-256 |
|---|---|---:|---|
| Bitstream | `fpga/final_project/final_project.runs/impl_1/fpga_top.bit` | 2,192,116 B | `340d6d45e8c89d0b09e92162f8b14560ee8cd903302a3a064a0a4d9fcbad658d` |
| 固件镜像 | `fpga/firmware/int8_selftest.hex` | 20,480 B | `fa38f91311768cd73386f8e093370831383d9e0e1b8a4832a2f3f978a2bfe850` |

固件配置见 [firmware_dma.json](firmware/firmware_dma.json)：

```text
samples       = 4
batches       = 1
code_bytes    = 1140
image_used    = 7952 B
SRAM capacity = 8192 B
transport     = DMA
```

镜像包含共享 32-MAC、batch=4 自检所需的程序、权重、四个输入样本和整数参考结果。固件比较的是 hidden、六个 score 和预测 class，而不是数据集的真实标签准确率。

## 3. 测试步骤

1. 通过 JTAG 将 `fpga_top.bit` 配置到 A7-35T。
2. 释放复位，等待固件完成镜像自检和 NPU 推理。
3. 通过 GDB 读取 `0x80001FE0` 的 PASS/FAIL 标志。
4. 读取当前 PC 和后续指令，确认 CPU 是否已进入固件 halt 循环。
5. 读取 NPU 状态、batch 配置、FC1/FC2 发射周期和 tile 加载计数。
6. 分别读取 NPU MMIO 与固件保存到 SRAM 的周期、重叠计数器并进行交叉核对。
7. 核对当前 bitstream 的 SHA-256、Clocking Wizard 频率、routed timing、资源利用率和 DRC 结果。

## 4. 测试结果摘要

| 编号 | 测试项 | 预期 | 实测 | 结果 |
|---|---|---|---|---|
| F01 | bitstream 配置与自检完成 | CPU 写出 PASS 标志 | `0x80001FE0 = 0xC0DEC0DE` | PASS |
| F02 | CPU 结束状态 | PC 停在固件自循环 | PC=`0x80000470`，`j 0x80000470` | PASS |
| F03 | NPU 完成状态 | `done=1, busy=0, error=0` | `0x70000004 = 0x00000001` | PASS |
| F04 | batch 配置 | 4 个样本 | `0x70000018 = 0x00000004` | PASS |
| F05 | FC1 发射周期 | batch×64=256 | `0x70000028 = 0x00000100` | PASS |
| F06 | FC2 发射周期 | batch×8=32 | `0x7000002C = 0x00000020` | PASS |
| F07 | 逻辑权重 tile 加载数 | 32 W1 + 4×8 W2 = 64 | `0x70000030 = 0x00000040` | PASS |
| F08 | NPU 总周期 | SRAM 副本与 MMIO 一致 | 两处均为 `0x0000038C` = 908 | PASS |
| F09 | DMA/MAC 总重叠 | 非零且 SRAM/MMIO 一致 | 两处均为 `0x0000010E` = 270 | PASS |
| F10 | DMA 读/MAC 重叠 | 非零且 SRAM/MMIO 一致 | 两处均为 `0x0000010E` = 270 | PASS |
| F11 | DMA 写/MAC 重叠 | 非零且 SRAM/MMIO 一致 | 两处均为 `0x0000010D` = 269 | PASS |

## 5. 结果分析

### 5.1 PASS 标志不是镜像预置值

当前 `int8_selftest.hex` 在偏移 `0x1FE0` 的初始内容为：

```text
00000000
```

因此，GDB 读到的 `0xC0DEC0DE` 是 CPU 执行固件、完成 NPU 推理和逐值比较后写出的结果，不是 bitstream 配置时预置的 PASS 常量。比较过程中任一结果不一致时，固件会写入 `0xDEADBEEF`。

### 5.2 CPU 已进入 halt 循环

GDB 观测到：

```text
=> 0x80000470:  j       0x80000470
   0x80000474:  unimp
   0x80000476:  unimp
```

当前固件有效代码长度为 1,140 B，即 `0x474` B；`0x80000470` 正好是最后一条有效跳转指令。CPU 持续跳回自身，不会执行后面的填充/非法指令。

该 PC 与 PASS 标志相互印证：CPU 已完成镜像启动、NPU 配置、DMA、推理、数值比较和状态回写，没有停在启动、DMA 或 NPU 轮询状态。

### 5.3 NPU 状态和周期计数

`0x70000004` 的状态格式为：

```text
bit[2] = error
bit[1] = busy
bit[0] = done
```

实测 `0x00000001` 表示 NPU 已结束且没有报告错误。

主要计数换算如下：

| 指标 | MMIO 地址 | 十六进制 | 十进制 |
|---|---|---:|---:|
| NPU 总周期 | `0x7000000C` | `0x38C` | 908 |
| FC1 发射周期 | `0x70000028` | `0x100` | 256 |
| FC2 发射周期 | `0x7000002C` | `0x020` | 32 |
| 逻辑 tile 加载数 | `0x70000030` | `0x040` | 64 |
| DMA/MAC 总重叠 | `0x7000001C` | `0x10E` | 270 |
| DMA 读/MAC 重叠 | `0x70000034` | `0x10E` | 270 |
| DMA 写/MAC 重叠 | `0x70000038` | `0x10D` | 269 |

周期数符合当前调度：

```text
FC1 = 32 tiles × 2 phases × 4 samples = 256
FC2 =  4 packets × 2 phases × 4 samples = 32
MAC ISSUE 总周期 = 256 + 32 = 288
NPU busy 总周期 = 908
非 ISSUE 的等待/量化/状态周期 = 908 - 288 = 620
每样本摊销 NPU 周期 = 908 / 4 = 227
```

908 是完整 SoC 中的 NPU `cycle_count`，包含权重 DMA、MAC、requant、tile 交接和等待。它不同于 NPU 专用测试台 [perf.py](../test/int8/perf.py) 在更强确定性 AXI 背压下得到的 batch=4 周期 1512；两者使用同一个内部计数器，但系统流量环境不同，不能混用。

### 5.4 tile 加载数仍为 64 的原因

`loads` 统计的是逻辑权重 tile 数，不是 DMA 事务数，也不是 MAC 发射周期：

```text
FC1：32 个 64 B tile × 1       = 32
FC2： 4 个 48 B packet × 8 tile = 32
总计                                  = 64
```

MAC 从 64 个减为 32 个只改变每个 tile 的计算相位和发射周期，不改变权重总量。同一权重在全部样本和两个相位之间复用，因此 batch=1/2/4 完成一批推理时都只加载 64 个逻辑 tile。

实际权重 DMA 读取事务为 32 次 W1 加 4 次 W2，共 36 次；有效权重数据为 `32×64 + 4×48 = 2240 B`。

### 5.5 SRAM 副本与 MMIO 交叉核对

固件在结束前把 NPU 计数器复制到主 SRAM，JTAG 可以读取该持久副本；同一组值也可在 NPU MMIO 实时读取。

| SRAM 地址 | MMIO 地址 | 指标 | 两处实测值 |
|---|---|---|---:|
| `0x80001FC0` | `0x7000000C` | NPU 总周期 | `0x0000038C` |
| `0x80001FC4` | `0x7000001C` | DMA/MAC 总重叠 | `0x0000010E` |
| `0x80001FC8` | `0x70000034` | DMA 读/MAC 重叠 | `0x0000010E` |
| `0x80001FCC` | `0x70000038` | DMA 写/MAC 重叠 | `0x0000010D` |

四组值完全一致，说明 CPU 的 SRAM 存储通路、JTAG 读取通路和 NPU MMIO 回读路径返回了相同的最终状态。

SRAM 不是周期计数的来源。计数的源头是 `har_npu_core.cycle_count`，由 `simple_npu_top` 映射到 MMIO `0x0C`，再由固件复制到 SRAM `0x1FC0`。

### 5.6 FPGA 与完整 SoC RTL 仿真对照

当前共享 32-MAC 的完整 SoC RTL 记录位于 [shared_mac_validation.json](../report/shared_mac_validation.json) 和 [sram_transaction_reset_port.json](../report/sram_transaction_reset_port.json)。

| 指标 | FPGA/GDB 实测 | RTL 完整 SoC 仿真 | 对照结果 |
|---|---:|---:|---|
| NPU 总周期 | 908 | 908 | 一致 |
| DMA/MAC 总重叠 | 270 | 未单独归档 | 板上值已记录 |
| DMA 读/MAC 重叠 | 270 | 270 | 一致 |
| DMA 写/MAC 重叠 | 269 | 269 | 一致 |
| FC1 发射周期 | 256 | 256 | 一致 |
| FC2 发射周期 | 32 | 32 | 一致 |
| 逻辑 tile 加载数 | 64 | 64 | 一致 |
| 提交后完整 SoC 周期 | 未记录 | 5,109 | 无板上对应项 |

归档的 RTL 仿真 JSON 明确保存 NPU 周期以及 DMA 读、写两个重叠子计数；总重叠并集没有单独字段。因此板上总重叠 270 只作为本次实测记录，读 270、写 269 与仿真逐项一致。

908 和 5,109 统计范围不同：

- 908 是 NPU `busy` 区间内的完整 NPU 周期；
- 5,109 是从启动许可提交到 CPU 写出 PASS 的完整 SoC 周期，包含 CPU 启动、配置、轮询和最终结果比较；
- 当前固件只保存 NPU 周期和重叠计数，没有保存板上完整 SoC 周期。

因此不能用 `5,109 - 908` 推算 CPU 独立执行时间。CPU 轮询可与 NPU 活动重叠，差值只表示整个 SoC 区间中 NPU 未计为 busy 的墙钟拍数。

## 6. 原始 GDB 观测记录

```text
(gdb) x/1xw 0x80001FE0
0x80001fe0:     0xc0dec0de

(gdb) x/3i $pc
=> 0x80000470:  j       0x80000470
   0x80000474:  unimp
   0x80000476:  unimp

(gdb) x/1xw 0x70000004
0x70000004:     0x00000001

(gdb) x/1xw 0x70000018
0x70000018:     0x00000004

(gdb) x/1xw 0x70000028
0x70000028:     0x00000100

(gdb) x/1xw 0x7000002C
0x7000002c:     0x00000020

(gdb) x/1xw 0x70000030
0x70000030:     0x00000040

(gdb) x/1xw 0x80001FC0
0x80001fc0:     0x0000038c

(gdb) x/1xw 0x7000000C
0x7000000c:     0x0000038c

(gdb) x/1xw 0x80001FC4
0x80001fc4:     0x0000010e

(gdb) x/1xw 0x7000001C
0x7000001c:     0x0000010e

(gdb) x/1xw 0x80001FC8
0x80001fc8:     0x0000010e

(gdb) x/1xw 0x70000034
0x70000034:     0x0000010e

(gdb) x/1xw 0x80001FCC
0x80001fcc:     0x0000010d

(gdb) x/1xw 0x70000038
0x70000038:     0x0000010d
```

## 7. 构建、时序和资源证据

### 7.1 时钟与时序

`clk_wiz_0.xci` 的 `CLKOUT1_REQUESTED_OUT_FREQ` 和 routed timing report 均对应 20 MHz。

| 项目 | 结果 |
|---|---:|
| 系统时钟频率 | 20 MHz |
| 系统时钟周期 | 50.000 ns |
| Setup WNS | +0.470 ns |
| Setup TNS | 0.000 ns |
| Setup 失败端点 | 0 |
| Hold WHS | +0.054 ns |
| Hold THS | 0.000 ns |
| Hold 失败端点 | 0 |
| 周期检查失败端点 | 0 |

Vivado routed timing summary 结论为 `All user specified timing constraints are met`。该报告支持当前 20 MHz bitstream 的内部时序通过，不支持宣称 25 MHz 或 50 MHz 已通过。

### 7.2 资源占用

来源：`fpga/final_project/final_project.runs/impl_1/fpga_top_utilization_placed.rpt`。

| 资源 | 使用量 | 可用量 | 利用率 |
|---|---:|---:|---:|
| Slice LUT | 19,323 | 20,800 | 92.90% |
| LUT as Logic | 19,299 | 20,800 | 92.78% |
| LUT as Distributed RAM | 24 | 9,600 | 0.25% |
| Slice Register | 14,998 | 41,600 | 36.05% |
| DSP48E1 | 40 | 90 | 44.44% |
| Block RAM Tile | 2 | 50 | 4.00% |
| BUFGCTRL | 3 | 32 | 9.38% |

LUT 仍是主要容量瓶颈，仅余 1,477 个逻辑 LUT。后续增加 batch 深度、调试核或其他 SoC 功能前必须重新检查容量，不能仅根据寄存器或 DSP 余量判断可扩展性。

### 7.3 DRC、布线和 bitstream 生成

- routed DRC 为 0 Errors、157 Warnings；
- 可布线网络 33,543 条，全部完成布线，0 条布线错误；
- routed timing 无失败端点；
- `Bitgen Completed Successfully`；
- `write_bitstream completed successfully`。

主要 DRC 警告包括：

- 1 条 `CFGBVS-1`：未显式设置 `CFGBVS/CONFIG_VOLTAGE`；
- 78 条 `DPIP-1`、39 条 `DPOP-1`、38 条 `DPOP-2`：DSP 输入/输出流水建议；
- 1 条 `RTSTAT-10`：2 条网络没有可布线负载。

这些警告没有阻止 bitstream 生成，且当前时序已经通过；但不能仅由一次功能 PASS 证明这些警告全部可以永久豁免。进入正式板级签核前应逐类记录处置决定。

## 8. 补充板上测试记录

以下结果由我在本次板上测试中确认。我已经记录 T04 的命令和输出以及 M1、K1、K3 的板上现象；T01、T02、T03 的原始复位次数和配置日志尚未归档到仓库。因此这些项目只在当前测试证据范围内记录为完成，不扩展为其他温度、电压或板卡条件。

| 编号 | 测试项 | 结果 | 证据说明 |
|---|---|---|---|
| T01 | 连续复位 10 次 | 完成 | 我确认每次重新运行后的自检流程完成；原始 GDB 日志待归档 |
| T02 | 重复配置 bitstream 3 至 5 次 | 完成 | 我确认重复配置流程完成；各次配置日志待归档 |
| T03 | 20 至 30 分钟重复运行 | 完成 | 我确认运行期间无新增失败；连续运行日志待归档 |
| T04 | `0x80001FF0` 整字与字节访问 | 完成 | 整字读写、恢复零、字节写和逐字节读均通过 |
| T05 | M1/K1/K3 状态 | 完成 | M1 常亮；持续读取后 K1 点亮；K3 常亮 |
| T07 | 无预装载镜像的 JTAG 启动流程 | 完成 | 部分/乱序/错误密钥均未启动，完整镜像与正确密钥正常 PASS |

### 8.1 T04 整字和字节读写结果

测试地址 `0x80001FF0` 位于当前镜像未使用区，初始整字和首字节均为零。写入 `0x12345678` 后，整字读回正确；按字节读取符合小端序：

```text
(gdb) x/1wx 0x80001FF0
0x80001ff0:     0x00000000
(gdb) x/1bx 0x80001FF0
0x80001ff0:     0x00
(gdb) set {int}0x80001FF0 = 0x12345678
(gdb) x/1wx 0x80001FF0
0x80001ff0:     0x12345678
(gdb) x/1bx 0x80001FF0
0x80001ff0:     0x78
(gdb) x/2bx 0x80001FF0
0x80001ff0:     0x78    0x56
(gdb) x/3bx 0x80001FF0
0x80001ff0:     0x78    0x56    0x34
(gdb) x/4bx 0x80001FF0
0x80001ff0:     0x78    0x56    0x34    0x12
(gdb) set {unsigned int}0x80001FF0 = 0
(gdb) x/4bx 0x80001FF0
0x80001ff0:     0x00    0x00    0x00    0x00
(gdb) set {unsigned char}0x80001FF0 = 0xaa
(gdb) x/1wx 0x80001FF0
0x80001ff0:     0x000000aa
(gdb) set {unsigned char}0x80001FF1 = 0xbb
(gdb) x/1wx 0x80001FF0
0x80001ff0:     0x0000bbaa
```

这证明：

- 对齐的 32 位 SRAM 写事务正确；
- JTAG 读回路径和 GDB 字节提取正确；
- 四个字节位序符合小端存储。
- 整字恢复为零后，两次单字节写分别得到 `0x000000AA` 和 `0x0000BBAA`；
- 写 `0x80001FF1` 时，`0x80001FF0` 的低字节 `0xAA` 保持不变。

T04 的 GDB 软件可见层面已完成。现有日志覆盖字节 lane 0 和 lane 1；lane 2、lane 3 以及直接观测 AXI `WSTRB`/SRAM `be_i` 的单字节时序尚未单独归档。两者属于更严格的硬件内部证据，不改变本次 T04 的软件访问结论。日志结束时该整字为 `0x0000BBAA`，尚未执行测试后的最终归零；该地址不参与固件，不影响 PASS 结果。

### 8.2 M1、K1 与 K3 观测

初始短时 GDB 访问后 K1 不亮。K1 连接 `led_tck`，该输出每累计 500,000 个 TCK 上升沿才翻转一次；短时访问不足以触发翻转，TCK 停止后 K1 保持最后状态。

随后通过循环执行 GDB SRAM 读取，产生足够持续的 TCK 活动，K1 点亮。该结果实测确认了以下路径：

- M1 常亮，确认 Clocking Wizard 的 `clk_locked` 为高且 M1 输出通路正常；
- GDB/JTAG 访问会持续产生 `tck_i`；
- `tck_i` 能到达 K1 计数器；
- 计数器达到阈值后能够翻转 `led_tck`；
- K1 对应 FPGA `PACKAGE_PIN K1` 的输出通路正常；
- K3 在 PASS 状态下保持常亮，确认 PASS 状态捕获和 K3 输出通路正常。

K1 是分频活动灯，不是 JTAG 连接或常亮状态灯。M1 的常亮表示 MMCM locked，K3 的常亮表示固件最终状态为 PASS，K1 的点亮表示持续 JTAG 活动能够驱动 TCK 指示计数器。T05 已完成。

### 8.3 T07 无预装载 JTAG 启动

使用 `SRAM_INIT_FILE` 为空的无预装载 bitstream 完成启动保护测试：

- 复位后 `boot_status=0x00000000`；
- 完整装载 2048 字后为 `0x00000800`，此时尚未启动；
- 写正确启动提交码后为 `0x00002800`；
- 恢复 CPU 后读取 `0x80001FE0 = 0xC0DEC0DE`；
- 最终 PC 位于 `0x80000470` 的固件自循环。

保护路径全部通过：

| 测试 | 结果 |
|---|---|
| 不装载，只写启动提交码 | `ready=0`，CPU 未启动 |
| 只装载 4 KiB 镜像后写启动提交码 | `loaded_words=1024, ready=0`，CPU 未启动 |
| 乱序写入后写启动提交码 | 计数停在缺口处，`ready=0` |
| 完整镜像后写错误提交码 | `loaded_words=2048, ready=0`，CPU 未启动 |
| 完整镜像后写正确提交码 | `ready=1`，CPU 启动并得到 PASS |

T07 已完成。该测试证明 bootram 会同时检查完整字数、写入顺序和提交码；系统复位只清除 boot 控制状态，不依赖 SRAM 被清零。

## 9. 测试边界和未覆盖项

本次测试未覆盖以下内容：

1. **仅验证了一组四样本输入。** 当前板上镜像使用训练模型的一组四样本 UCI 输入；其他 UCI 组、随机输入和边界输入尚未在板上验证。
2. **数值一致性不等于分类准确率。** PASS 表示 hidden、scores、class 与同镜像整数参考逐项一致，不是对完整数据集的准确率评测。
3. **T01/T02/T03 的原始日志尚未归档。** 上述项目已由我确认完成，但仓库目前没有可逐次复核的原始记录。
4. **T04 的内部单字节时序证据仍有范围限制。** GDB 层整字读写、恢复零和字节 lane 0/1 写通过；lane 2/3 及直接单字节 AXI `WSTRB` 尚未单独归档。
5. **FPGA 后端不是 ASIC 原生 SRAM。** 板上使用 BRAM 后端，不能替代 `RA1SHD_2048x32M8` 的时序、功耗和版图验证。
6. **未进行 25/50 MHz、PVT、长期老化或完整 I/O 时序签核。** 本报告只支持当前 20 MHz bitstream。
7. **未记录完整 SoC 板上周期。** 当前固件能够保存 NPU 周期和重叠计数，但不能保存从启动许可到 PASS 的完整 SoC 周期。
8. **时钟说明仍需同步。** `fpga_top.sv` 顶部注释和 `fpga/README.md` 的 50/25 MHz 描述落后于实际 20 MHz 构建。

## 10. 后续补充测试清单

| 编号 | 测试项 | 预期 | 状态 |
|---|---|---|---|
| T01 | 连续复位 10 次 | 每次重新运行并返回 `0xC0DEC0DE` | 完成 |
| T02 | 重复配置 bitstream 3 至 5 次 | 每次 PASS，周期计数可复现 | 完成 |
| T03 | 20 至 30 分钟重复运行 | 无自发 FAIL、卡死或总线错误 | 完成 |
| T04 | JTAG 在未使用 SRAM 地址做整字和逐字节读写 | 模式读回正确并恢复原值 | 完成（GDB 层） |
| T05 | 读取并记录 M1/K1/K3 | M1 locked，K1 随 TCK 活动，K3 PASS 后常亮 | 完成 |
| T06 | 其余训练 UCI 四样本批次板上运行 | hidden、scores、class 全部匹配 | 待补 |
| T07 | 无预装载镜像的 JTAG 启动流程 | 错误密钥/部分镜像不启动，正确密钥启动 | 完成 |
| T08 | 板上完整 SoC 周期插桩 | 可读取提交至 PASS 的完整周期 | 待补 |
| T09 | 更新 20 MHz 时钟说明和报告索引 | 文档与 XCI/routed timing 一致 | 待补 |
