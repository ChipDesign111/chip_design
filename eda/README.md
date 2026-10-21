# 完整 SoC ASIC 验证流程

此流程面向当前 CV32E40P、AXI、DMA 和 HAR NPU 的完整 `my_soc_top`，包含综合前后的功能与时序基线，以及 Innovus 布局、CTS、布线和物理检查。它使用课程 TSMC180 标准单元和主 SRAM 宏进行实际工艺映射；原 `tools/project.py synth` 仍是 Yosys 通用结构检查。

本次实测状态、面积、时序与后续工作见 [结果记录](RESULTS.md)。

2026-10-21 完整 SoC 的 route / finish / export 已完成，最终 setup +1.217 ns、hold +0.018 ns，TNS、违反端点、DRV 和最终布线 DRC 均为 0；独立连接与几何审计 8/8 通过。布线后 SDF 在明确的 1000 ns 先复位后起钟协议下，MAX/MIN 四个完整场景均已实际 PASS，详见 [PNR 结果](pnr/RESULTS.md) 和 [PNR 入口](pnr/README.md)。

## 验证顺序

| 阶段 | 输入和判据 |
| --- | --- |
| RTL 前仿 | Xcelium 编译当前 RTL，使用真实 SRAM 模型，经顶层 JTAG 下载完整 2048 字并回读；CPU 执行固件自检 |
| 工艺综合 | Genus 将逻辑映射到 TSMC180 TT 1.8 V 25 C 单元；检查链接、面积、setup、时钟和约束 |
| 门级功能后仿 | 相同固件和引脚测试台，替换为综合网表和标准单元模型；关闭 specify 和 timing checks，使用官方 UDP NBA 调度选项检查映射后功能 |
| 综合后 SDF 仿真 | 对同一门级网表注入 TT 的 MAXIMUM 延时；保留 specify 和 timing checks，检查注入与动态时序结果 |
| 证据汇总 | 比对固件、源文件与输出哈希，检查 SRAM 宏数量、SDF 层次和每个阶段实际日志 |
| 布局布线与静态检查 | 使用同一完整 SoC 网表执行 Innovus floorplan / IO / power / place / CTS / route / finish / export；审计 setup/hold、DRC、天线、PG、原生 IO 轨和导出文件身份 |
| 布线后 SDF 仿真 | 使用最终提取与 IO 单元模型进行 MAX / MIN 引脚级动态验证；1000 ns 上电协议下 MAX/MIN 四场景实际 PASS，判据来自各场景原始日志与独立审计 |

系统时钟固定为 20 ns，JTAG TCK 为 100 ns。`synthetic` 固件覆盖 39 周期单样本、59 周期双样本、量化边界与逐项结果；`dma` 固件覆盖 24 个真实样本的隐藏值、得分、类别及 DMA 完成检查。每个正例做两次新复位启动，先清除旧完成标记；RTL 还执行下载损坏负例。测试台不写入或强制 DUT 内部节点，也不依赖综合网表中的内部实例名字。

综合后 SDF 使用布线前估计，不包含实际 CTS 和布线寄生。Genus 19.17 原生 `report_timing` 不支持 `-early`；本设计的静态 hold 现已在最终 Innovus 数据库上检查。综合后 SDF 的 PASS 与布线后 SDF 的动态验收分别记录，原 CPU 模板的 Lab 4 结果也不作为本设计证据。当前课程 TT 单角结果尚不覆盖全 PVT、独立形式等价或 foundry 签核。

## 工艺和存储选择

默认工艺库根目录为 `/lec/pdk/tsmc180`，默认 SRAM 材料为 `/lec/lab4/soc_cv32e40p_template_pnr-stu/src/macro/RA1SHD_2048x32M8`。可用环境变量 `CHIP_PDK_ROOT`、`CHIP_SRAM_ROOT` 或命令参数覆盖。

主存通过 `CHIP_USE_RA1SHD` 映射为一个 2048×32 SRAM 宏，综合使用 Liberty，前后仿使用配套 Verilog 模型。NPU 的 38 个权重 bank 有独立计算读和 CPU 回读端口，本流程将它们映射为标准单元；不能直接用单口主 SRAM 宏替换。最终面积应依据本次综合报告。

工艺模型、库和 EDA 许可证由运行环境提供，不复制到仓库。生成网表、SDF、数据库、完整日志和仿真临时文件统一保存在忽略目录 `eda/work/`。

## 运行

在课程 Linux 服务器上加载已有 EDA 环境，在仓库根目录运行。驱动脚本只需 Python 3.8 标准库，固件已固定并附哈希。

```sh
source /opt/eda/env.sh
source /lec/eda.env
python3 eda/run_flow.py --out eda/work/asic-example
```

每次选择新的输出目录。流程会在错误时停止，结果写入 `flow.json` 和 `verification.json`；不能仅凭工具正常退出判断验收通过。`--dry-run` 只生成命令清单，不执行或声明仿真成功。

需要分阶段运行或检查已有结果时，使用以下入口：

```sh
python3 eda/syn/run_synthesis.py --help
python3 eda/sim/run_pins.py --help
python3 eda/check_results.py --help
```

`run_pins.py` 的 `rtl`、`gate`、`sdf` 模式共用 [tb_soc_pins.sv](sim/tb_soc_pins.sv) 和 [固件清单](sim/firmware/manifest.json)。SDF 模式使用 `xmsdfc` 和 `xrun -sdf_cmd_file`，拒绝禁用时序检查的参数。验收检查控制台的实际注入统计、未匹配项和 timing violation；`sdf_unannotated.log` 是未注入项清单，全部注入时可以为空，不能拿它作为已注入数量。

门级功能仿真必须增加 `--xrun-arg=-sequdp_nba_delay`，一键流程已加入。该官方选项将零延迟时序 UDP 的输出更新放入 NBA 队列，避免标准单元和 SRAM 宏在同一时刻采样的竞态；它不增加时间延迟。SDF 模式使用真实时延和 `NTC/RECREM/-negdelay` 库配置，不添加该零延迟调度选项。

## 约束和诊断

[constraints.sdc](syn/constraints.sdc) 保留课程的 20 ns 系统时钟、100 ns JTAG 时钟、1000 ns 虚拟 JTAG 时钟及不确定度，并补充输入电气模型和输出负载。异步复位例外属于当前教学约束假设。CDC 的 12 ns 最大延时约束需检查实际匹配对象与路径；报告脚本保存 CDC 网名、数量及路径，避免空集合造成假约束。

Genus 19.17 必须先 `read_mmmc` 建立目标库域，再 `set_db lef_library`。反序会在建立物理库单位时产生两条 `LBR-163` 和单位警告。相关独立探针保存在 [probes](syn/probes)，没有修改或屏蔽工艺库消息。

面积报告是单元面积，不是 Die 面积；默认开关概率得到的功耗是估算。当前 floorplan 已按完整 SoC 的 SRAM、单元面积、IO 和电源空间重做，实际 Die 为 3400.32 × 3400.32 μm，core 为 3100.16 × 3100.16 μm。规划依据保留在 [PHYSICAL_PLAN.md](PHYSICAL_PLAN.md)，最终数据见 [PNR 结果](pnr/RESULTS.md)。

当前 SoC 保留四级同步器，并在其后增加下降沿复位释放寄存器，给正沿电路留出 recovery/removal 余量；原因和原始失败数据见 [启动与复位协议](BOOT_PROTOCOL.md)。原全局复位 false-path 的教学约束不代表已经完成所有异步复位签核。
