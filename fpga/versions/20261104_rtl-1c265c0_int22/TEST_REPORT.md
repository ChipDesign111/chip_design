# FPGA 测试报告：2026-11-04 INT22

## 测试结论

当前 INT22 RTL 对应的无预装 FPGA bitstream 已通过 A7-35T 板上自检、
扩展复位/重配置/长时间运行回归和 SRAM 四字节访问检查。CANONICAL 镜像完成
batch=4 推理、整数结果比较和 PASS 回写，最终进入固件自循环。

| 项目 | 结果 |
|---|---|
| 测试日期 | 2026-11-04 |
| FPGA | Xilinx Artix-7 `xc7a35tcsg324-1` |
| 系统时钟 | 20 MHz |
| Bitstream SHA-256 | `bdf36e5888703ebc6905f3cd87a4f42b8256168484147baf97b966e9d47d326e` |
| Canonical 镜像 SHA-256 | `3f1dcd0eaf725269e52cd39e9e6917138e8f8ed932fa0d4f61fa81fe4175ee4b` |
| 板上结果 | PASS |

## 编译和实现

| 检查项 | 结果 |
|---|---|
| 预装固件 | 否，`SRAM_INIT_FILE` 为空 |
| Synthesis errors / critical warnings | 0 / 0 |
| Implementation errors | 0 |
| Routed DRC errors | 0 |
| 布线 | 全部可布网络完成布线 |
| Setup WNS / Hold WHS | `+0.407 / +0.034 ns` |
| Slice LUT | `17,625 / 20,800`，84.74% |
| Slice Register | 13,855 |
| DSP48E1 | 40 |
| Block RAM Tile | 2 |

详细时序、资源和布线证据见 [reports](reports/) 与 [logs](logs/)。

## RTL 回归

- 38/38 单元用例通过。
- 24 条训练输入通过。
- 完整 SoC 通过。
- RTL 观测窗口 `6369` 拍，硬件计数器 `6364` 拍。
- NPU `975` 拍，FC1/FC2 发射周期 `256/64`。
- DMA 读/写与 MAC 重叠均为 `278` 拍。

证据见 [soc.log](evidence/soc.log)、[result.json](evidence/result.json) 和
[firmware.S](evidence/firmware.S)。

## 与前仿结果对比

| 指标 | RTL 前仿 | MAXIMUM SDF 后仿 | A7-35T 板级 |
|---|---:|---:|---:|
| 功能结果 | PASS | PASS | PASS |
| NPU cycles | 975 | 975 | 975 |
| FC1 issue cycles | 256 | 256 | 256 |
| FC2 issue cycles | 64 | 64 | 64 |
| DMA read/MAC overlap | 278 | 278 | 278 |
| DMA write/MAC overlap | 278 | 278 | 278 |
| DMA/MAC total overlap | 未单独输出 | 279 | 279 |
| SoC cycles | 6364 硬件 / 6369 TB | 6370 | 6368 |

RTL 前仿的 NPU 周期、FC1/FC2 发射周期及 DMA 读/写重叠与板测逐项一致；
MAXIMUM SDF 后仿的代表结果也与板测一致。完整 SoC 周期不作为逐拍相等指标：
RTL 硬件计数器从首次非 debug 取指启动，testbench 还包含不同的观测窗口，
而板测经过 JTAG debug resume。因此板端 `6368` 与 RTL 硬件口径 `6364` 相差
4 拍，比 testbench 观测窗口 `6369` 少 1 拍，符合不同启动与观测边界，不影响
NPU 和功能计数的一致性判定。

后仿来源见
[INT22 MAXIMUM SDF results](../../../eda/results/int22_20261104/postsim/results.json)。

## 板上功能结果

| 观察项 | 实测值 | 结论 |
|---|---:|---|
| Boot status | `0x00002800` | 2048 words 已装载并提交 |
| PASS 标志 `0x80001FE0` | `0xC0DEC0DE` | PASS |
| 最终 PC | `0x80000470` | 位于固件自循环 `j 0x80000470` |
| NPU status `0x70000004` | `0x00000001` | `done=1, busy=0, error=0` |
| Batch `0x70000018` | 4 | 正确 |
| 权重 tile loads `0x70000030` | 64 | 正确 |
| FC1 issue cycles `0x70000028` | 256 | 正确 |
| FC2 issue cycles `0x7000002C` | 64 | 正确 |
| NPU cycles `0x7000000C` | 975 | 与 SRAM 副本一致 |
| DMA/MAC overlap `0x7000001C` | 279 | 与 SRAM 副本一致 |
| DMA read/MAC overlap `0x70000034` | 278 | 与 SRAM 副本一致 |
| DMA write/MAC overlap `0x70000038` | 278 | 与 SRAM 副本一致 |
| SoC cycles `0x00010038` | 6368 (`0x000018E0`) | 与 MMIO 镜像一致 |

原始 GDB 记录见 [board_gdb_20261104.txt](evidence/board_gdb_20261104.txt)。

## 板级扩展回归

以下项目均已在 A7-35T 板上执行并通过：

| 项目 | 结果 |
|---|---|
| LED 状态 | PASS：M1 表示 MMCM locked，K1 表示 TCK 活动，K3 表示最终 PASS |
| 连续复位 | PASS |
| 重复 bitstream 重配置 | PASS |
| 长时间运行压力测试 | PASS |

本次粘贴的 GDB 片段只包含主功能计数和 SRAM 访问探针；上述扩展回归的逐次
原始日志未包含在该片段中。

## SRAM 访问检查

在未使用地址 `0x80001FF0` 完成以下检查：

- 32-bit 字写入 `0x12345678` 后读回一致。
- 恢复为整数零后读回 `0x00000000`。
- byte 0 写入 `0xAA` 后读回 `0x000000AA`。
- byte 1 写入 `0xBB` 后读回 `0x0000BBAA`。
- 连续写入 byte 0/1/2/3 为 `AA/BB/CC/DD` 后读回 `0xDDCCBBAA`。
- 逐字节读取顺序为 `78 56 34 12`，符合小端布局。

byte 2/3 的补充写入与读回补齐了四个 byte lane 的软件可见访问检查。

## 判定

当前版本功能、A7-35T 板上主路径、LED、连续复位、重复重配置和长时间运行
回归均判定为 PASS。报告适用范围为该 bitstream、canonical 镜像、20 MHz
和本次 A7-35T 板卡条件；不扩展为 PVT、25/50 MHz 或完整数据集准确率签核。
