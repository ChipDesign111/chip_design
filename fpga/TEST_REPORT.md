# HAR SoC FPGA 板上测试报告

| 项目 | 内容 |
|---|---|
| 报告日期 | 2026-10-29 |
| 测试状态 | **PASS（当前 bitstream 单次板上功能验证）** |
| Git 分支 | `fpga` |
| Git 基线提交 | `0b12122 chore(fpga)` |
| FPGA 器件 | Xilinx Artix-7 `xc7a35tcsg324-1` |
| 顶层设计 | `fpga_top` |
| 系统时钟 | 25 MHz |
| 构建工具 | Vivado 2019.1 |
| 测试方法 | JTAG 配置 bitstream、板上 LED 观察、GDB/JTAG 读取 SRAM 和 MMIO |

## 1. 测试结论

当前 bitstream 已在 A7-35T FPGA 上完成一次端到端功能自检。CPU 从上电预装载的 8 KiB 镜像启动，完成 DMA 权重传递、INT8 NPU 推理、参考结果比较和状态回写。最终：

- K3 常亮，对应 `TEST_PASS`；
- `0x80001FE0` 读到 `0xC0DEC0DE`；
- CPU 程序计数器停在固件末尾的原地跳转循环；
- NPU 状态为 `done=1, busy=0, error=0`；
- FC1、FC2 和 tile 加载计数均为 64；
- DMA 读/MAC 重叠为 62 拍，DMA 写/MAC 重叠为 93 拍；
- SRAM 中保存的计数器与直接读取 MMIO 得到的值一致。

该结果证明当前 bitstream 在当前板卡和当前运行条件下完成了完整的数字功能路径。它不等同于全输入集、长期稳定性、50 MHz、ASIC 原生 SRAM 或 PVT 条件验证，具体边界见第 8 节。

## 2. 被测对象与构建产物

### 2.1 构建状态

测试时仓库位于 `fpga` 分支，HEAD 为 `0b12122acaee6cdd31a1e848ede33fe0ee458d2d`。工作区中的 Clocking Wizard 和 Vivado 工程文件仍有未提交改动：

```text
M fpga/final_project/final_project.srcs/sources_1/ip/clk_wiz_0/clk_wiz_0.xci
M fpga/final_project/final_project.xpr
```

当前 XCI 配置的系统时钟输出为 25 MHz。这些改动是本次 bitstream 的配置来源之一，不应在归档或复测前丢弃。

### 2.2 产物和校验值

| 产物 | 路径 | 大小 | SHA-256 |
|---|---|---:|---|
| Bitstream | `fpga/final_project/final_project.runs/impl_1/fpga_top.bit` | 2,192,116 B | `efe375c290144613416d0f45b2267153cddb3147cb57568e4faa2511a3608c0d` |
| 固件镜像 | `fpga/firmware/int8_selftest.hex` | 20,480 B | `e4c5b0a4245f719bd2399c1273abf1a19b9b1a38f8364f81686b0fa9e3946f5c` |

Bitstream 生成时间为 2026-10-29 10:49:29。Vivado routed timing report 的生成时间为 2026-10-29 10:41:04。

当前镜像包含训练模型的第一组双样本 UCI 输入。自检会把两个样本的 hidden、scores 和 class 与整数参考值逐项比较；任一比较失败会写入 `0xDEADBEEF`，全部通过才会写入 `0xC0DEC0DE`。

## 3. 测试步骤

1. 通过 JTAG 将 `fpga_top.bit` 配置到 A7-35T FPGA。
2. 释放复位，等待板上自检完成。
3. 观察 K3 指示灯。根据顶层 RTL，K3 在 `TEST_PASS` 时常亮，在 `TEST_FAIL` 时快速闪烁，其余状态显示普通心跳。
4. 通过 JTAG/GDB 读取 SRAM 的 PASS 标志、停机地址及相关计数。
5. 直接读取 NPU MMIO，并与 CPU 保存到 SRAM 的计数器副本交叉核对。
6. 读取当前 PC 和后续指令，确认 CPU 已完成自检并停留在安全循环。

## 4. 测试结果摘要

| 编号 | 测试项 | 预期 | 实测 | 结果 |
|---|---|---|---|---|
| F01 | Bitstream 配置 | 配置成功，系统运行 | K3 常亮 | PASS |
| F02 | 固件自检标志 | `0x80001FE0 = 0xC0DEC0DE` | `0xC0DEC0DE` | PASS |
| F03 | CPU 结束状态 | PC 停在固件 halt 自循环 | PC 指向 `0x800002C8` 的 `j 0x800002C8` | PASS |
| F04 | NPU 完成状态 | `done=1, busy=0, error=0` | `0x70000004 = 0x00000001` | PASS |
| F05 | Batch 配置 | 2 个样本 | `0x70000018 = 0x00000002` | PASS |
| F06 | FC1 计算拍数 | 64 | `0x70000028 = 0x00000040` | PASS |
| F07 | FC2 计算拍数 | 64 | `0x7000002C = 0x00000040` | PASS |
| F08 | 权重 tile 加载数 | 64 | `0x70000030 = 0x00000040` | PASS |
| F09 | NPU 总周期数 | SRAM 副本与 MMIO 一致 | 两处均为 `0x0000040B` | PASS |
| F10 | DMA/MAC 总重叠 | 非零，SRAM 副本与 MMIO 一致 | 两处均为 `0x0000005D` | PASS |
| F11 | DMA 读/MAC 重叠 | 非零，SRAM 副本与 MMIO 一致 | 两处均为 `0x0000003E` | PASS |
| F12 | DMA 写/MAC 重叠 | 非零，SRAM 副本与 MMIO 一致 | 两处均为 `0x0000005D` | PASS |

## 5. 结果分析

### 5.1 PASS 标志不是镜像预置值

`int8_selftest.hex` 在偏移 `0x1FE0` 的初始内容为 `0x00000000`。因此，本次读到的 `0xC0DEC0DE` 不是 bitstream 配置时直接写入 SRAM 的常数，而是 CPU 执行固件、启动 NPU 并完成全部数值比较后写出的结果。

GDB 同时读到的 `0x80001FE4` 至 `0x80001FF4` 均为零，没有观察到相邻状态区残留非零数据。

### 5.2 CPU 已进入固件 halt 循环

PC 指向：

```text
0x800002C8: j 0x800002C8
```

这是固件最后写入 PASS/FAIL 状态后的原地跳转。后面的 `unimp` 是反汇编看到的填充/非法指令，由于 CPU 持续跳回 `0x800002C8`，这些指令不会被顺序执行。

该现象与 `0xC0DEC0DE` 标志相互印证：CPU 已经到达固件末尾，并未卡在启动、DMA 或 NPU 等待状态。

### 5.3 NPU 状态和计数

`0x70000004` 的格式为：

```text
bit[2] = error
bit[1] = busy
bit[0] = done
```

实测 `0x00000001` 表示：

- `error = 0`；
- `busy = 0`；
- `done = 1`。

主要计数换算如下：

| 指标 | 十六进制 | 十进制 |
|---|---:|---:|
| NPU 总周期 | `0x40B` | 1,035 |
| FC1 周期 | `0x40` | 64 |
| FC2 周期 | `0x40` | 64 |
| 权重 tile 加载数 | `0x40` | 64 |
| DMA/MAC 总重叠 | `0x5D` | 93 |
| DMA 读/MAC 重叠 | `0x3E` | 62 |
| DMA 写/MAC 重叠 | `0x5D` | 93 |

64 次 tile 加载对应 FC1 的 32 个 tile 和 FC2 的 32 个 tile。FC1、FC2 各累计 64 个有效计算周期，符合双样本配置。

重叠计数器不是互斥分类。`overlap_count` 统计“DMA 读或 DMA 写与 MAC 同时活动”的周期，而读、写重叠分别统计各自子条件。因此总重叠 93、读重叠 62、写重叠 93 是可能的；总重叠不应简单写成 `62 + 93`。

### 5.4 SRAM 副本与 MMIO 交叉核对

固件在结束时把 NPU 的周期和重叠计数保存到 SRAM：

| SRAM 地址 | MMIO 地址 | 指标 | 两处实测值 |
|---|---|---|---:|
| `0x80001FC0` | `0x7000000C` | NPU 总周期 | `0x0000040B` |
| `0x80001FC4` | `0x7000001C` | DMA/MAC 总重叠 | `0x0000005D` |
| `0x80001FC8` | `0x70000034` | DMA 读/MAC 重叠 | `0x0000003E` |
| `0x80001FCC` | `0x70000038` | DMA 写/MAC 重叠 | `0x0000005D` |

四组值完全一致，说明 CPU 的 SRAM 存储通路、JTAG 读取通路和 NPU MMIO 回读路径均能返回相同的最终状态。

## 6. 原始 GDB 观测记录

```text
(gdb) x/6xw 0x80001FE0
0x80001fe0:     0xc0dec0de      0x00000000      0x00000000      0x00000000
0x80001ff0:     0x00000000      0x00000000

(gdb) x/3i $pc
=> 0x800002c8:  j       0x800002c8
   0x800002cc:  unimp
   0x800002ce:  unimp

(gdb) x/1wx 0x70000004
0x70000004:     0x00000001

(gdb) x/1wx 0x70000018
0x70000018:     0x00000002

(gdb) x/1wx 0x70000028
0x70000028:     0x00000040

(gdb) x/1wx 0x7000002C
0x7000002c:     0x00000040

(gdb) x/1wx 0x70000030
0x70000030:     0x00000040

(gdb) x/1wx 0x80001FC0
0x80001fc0:     0x0000040b

(gdb) x/1wx 0x7000000C
0x7000000c:     0x0000040b

(gdb) x/1wx 0x80001FC4
0x80001fc4:     0x0000005d

(gdb) x/1wx 0x7000001C
0x7000001c:     0x0000005d

(gdb) x/1wx 0x80001FC8
0x80001fc8:     0x0000003e

(gdb) x/1wx 0x70000034
0x70000034:     0x0000003e

(gdb) x/1wx 0x80001FCC
0x80001fcc:     0x0000005d

(gdb) x/1wx 0x70000038
0x70000038:     0x0000005d
```

## 7. 构建、时序和资源证据

### 7.1 时序

`fpga/final_project/final_project.runs/impl_1/fpga_top_timing_summary_routed.rpt` 给出的内部系统时钟结果：

| 项目 | 结果 |
|---|---:|
| 系统时钟频率 | 25 MHz |
| Setup WNS | +1.841 ns |
| Setup TNS | 0.000 ns |
| Setup 失败端点 | 0 |
| Hold WHS | +0.037 ns |
| Hold THS | 0.000 ns |
| Hold 失败端点 | 0 |
| 周期检查失败端点 | 0 |

该报告支持本次 25 MHz 工作点完成内部时序签核，但不支持宣称 50 MHz 已通过。Hold 余量为 0.037 ns，属于较紧的通过结果，建议后续通过重复复位和长时间运行补充板级稳定性证据。

### 7.2 资源占用

`fpga/final_project/final_project.runs/impl_1/fpga_top_utilization_placed.rpt` 记录：

| 资源 | 使用量 | 可用量 | 利用率 |
|---|---:|---:|---:|
| Slice LUT | 15,298 | 20,800 | 73.55% |
| Slice Register | 9,972 | 41,600 | 23.97% |
| DSP48E1 | 77 | 90 | 85.56% |
| Block RAM Tile | 2 | 50 | 4.00% |

### 7.3 DRC 和 bitstream 生成

- `place_design`、`route_design` 前置 DRC 均为 0 Errors。
- routed DRC 为 0 Errors、503 Warnings。
- 警告包括配置 bank 电压属性 `CFGBVS/CONFIG_VOLTAGE` 未显式设置、DSP 流水/异步复位建议等。
- `Bitgen Completed Successfully`，`write_bitstream completed successfully`。

DRC 警告没有阻止 bitstream 生成，也不能由一次功能 PASS 证明全部被合理豁免。若进入更正式的板级或交付签核，应记录并处理 `CFGBVS/CONFIG_VOLTAGE` 等配置类警告。

## 8. 测试边界和未覆盖项

本次测试未覆盖以下内容：

1. **仅验证了一组双样本输入。** 当前板上镜像使用训练模型第一组 UCI 输入。其他 UCI 样本、随机输入和边界输入尚未在板上验证。
2. **数值一致性不等于分类准确率。** 当前 PASS 表示 hidden、scores、class 与同镜像整数参考值逐项一致，不表示对完整数据集的分类准确率已经通过硬件评测。
3. **未完成复位和冷启动重复性验证。** 本次记录是一次成功运行，尚未给出连续复位、重新配置或断电重启的统计结果。
4. **未测试板上 SRAM 随机读写和逐字节写。** 当前固件主要使用整字访问；需要单独用 JTAG 对未使用地址做字/字节模式测试。
5. **未走完整的 JTAG 镜像装载和 commit 保护路径。** 当前 bitstream 设置了非空 `FPGA_INIT_FILE`，BRAM 在配置时预装载，`bootram` 使用 `PREINITIALIZED=1` 路径自动放行 CPU；因此错误密钥、部分镜像和顺序完整装载保护未被本次板上运行覆盖。
6. **FPGA 后端不是 ASIC 原生 SRAM。** 板级运行使用可移植 BRAM 行为后端，不能替代 `RA1SHD_2048x32M8` 宏的 `WEN`、时序、功耗和版图验证。
7. **未进行 50 MHz、PVT、长期老化或眼图/外部接口时序测试。** 当前结论仅适用于 25 MHz、当前 bitstream、当前室温单次运行。
8. **板级 I/O 时序未完整签核。** Vivado check_timing 仍报告部分 reset/LED/JTAG 端口未设置 input/output delay；该问题不影响本次内部自检结论，但不应视为完整板级时序签收。

## 9. 后续补充测试清单

| 编号 | 测试项 | 预期 | 状态 |
|---|---|---|---|
| T01 | P15 连续复位 10 次 | 每次重新运行并返回 `0xC0DEC0DE` | 待补 |
| T02 | 重复配置 bitstream 3 至 5 次 | K3 常亮且状态一致 | 待补 |
| T03 | 20 至 30 分钟重复运行 | 无自发 FAIL、卡死或总线错误 | 待补 |
| T04 | JTAG 在 `0x80001FF0` 做整字和字节读写 | 模式读回正确并恢复原值 | 待补 |
| T05 | 其余训练 UCI 样本板上运行 | hidden、scores、class 全部匹配 | 待补 |
| T06 | 无预装载镜像的 JTAG 启动流程 | 错误密钥/部分镜像不启动，正确密钥启动 | 待补 |
| T07 | 记录 M1 locked 和 K1 TCK 指示 | M1 常亮，K1 随 JTAG 活动闪烁 | 待补 |
| T08 | 归档最终 bitstream、固件、报告 | SHA-256 和构建配置一致 | 部分完成 |

## 10. 修订记录

| 日期 | 版本 | 内容 |
|---|---|---|
| 2026-10-29 | v0.1 | 新建报告；记录首次板上 PASS、GDB/JTAG 状态读取、25 MHz routed 时序、资源和当前测试边界 |
