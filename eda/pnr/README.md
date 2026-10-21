# 完整 SoC Innovus 物理实现

输入是已通过 [综合与引脚级前后仿](../RESULTS.md) 的完整 `my_soc_top`，不是原 Lab 4 CPU 模板网表。RTL、固件和原引脚测试台保持冻结。本目录新增物理实现、审计和布线后仿真入口；实际验收见 [结果记录](RESULTS.md)。

## 阶段与恢复

流程为 `init → floorplan → io → power → place → cts → route → finish → export`。系统/JTAG 周期保持 20/100 ns，虚拟参考时钟 1000 ns，setup/hold uncertainty 保持 0.52/0.2 ns，不使用额外 path adjustment。主 SRAM 采用课程宏，权重 bank 保留综合得到的标准单元实现。

初始 Die 为 3400.32 μm 见方，工具生成实际 core/site/row；SRAM 实例为 `i_mainmem/i_sram/i_macro`。PAD、Bond、filler、供电区域和引脚标签从实际 bbox 推导。名义 TT 标准单元/SRAM 为 1.8 V，IO 库为 3.3 V，温度 25 °C。使用课程原生六金属 captable 做布线后寄生提取。

在课程 EDA 环境和 Python 3.8+ 标准解释器下运行，避开其他 EDA 软件私有的 Python/Tcl 解释器：

```sh
python3 eda/pnr/run_pnr.py --out eda/work/pnr-example
```

也可以逐段执行；每次运行产生独立 invocation 日志、源码快照、输入哈希及时间戳 checkpoint：

```sh
python3 eda/pnr/run_pnr.py --out eda/work/pnr-example --stages init floorplan io power
python3 eda/pnr/run_pnr.py --out eda/work/pnr-example --resume /absolute/path/to/power-TIMESTAMP.enc.dat --stages place cts
```

检查点旁的 `.context.tcl` 保存物理辅助程序及状态，恢复时与数据库配套。失败阶段应从其前一个已完成检查点重跑。`COMPLETED` 只表示工具执行完成，最终时序、连通性、DRC 与仿真需要独立验收，不能仅看退出码。

## 布线后验证

`export` 导出实际 DEF、GDS、SPEF、SDC、空的 path-adjust 文件、带 PG 的物理/LVS 网表、去 PG 的层次功能网表，以及两份提取后 SDF：`my_soc_top_tt_io.sdf.gz` 保留原始 STA 延时，`my_soc_top_tt_io_gls.sdf.gz` 用于兼容门级仿真。两份 SDF 使用相同的显式 STA 参数，后者只增加 `-filter`；已有 SDF 会阻止覆盖。功能仿真使用层次功能网表及配套标准单元、SRAM、IO 模型。

```sh
python3 eda/pnr/run_postroute.py --netlist FINAL_HIER_POSTPNR.v --sdf FINAL_TT_IO_GLS.sdf.gz --out eda/work/postroute-max --sdf-corner MAXIMUM --xrun-arg=-caint
python3 eda/pnr/run_postroute.py --netlist FINAL_HIER_POSTPNR.v --sdf FINAL_TT_IO_GLS.sdf.gz --out eda/work/postroute-min --sdf-corner MINIMUM --xrun-arg=-caint
```

两组固定固件均需经真实 JTAG 下载/回读全部 2048 字、两次复位执行和结果自检；时序检查保持启用。`--dry-run` 不执行仿真，不能作为 PASS。

正式验收使用独立调度入口，并发运行同一 corner 的两组固件，按下文的外部上电协议延后起钟 1000 ns。每次必须显式指定全新的 `--out`，MAX/MIN 使用不同目录；以下两条可同时启动，合计最多四个仿真 worker，须为它们预留足够的内存和 CPU：

```sh
python3 eda/pnr/run_postroute_parallel.py --parallel 2 --netlist FINAL_HIER_POSTPNR.v --sdf FINAL_TT_IO_GLS.sdf.gz --out eda/work/postroute-parallel-max --sdf-corner MAXIMUM --xrun-arg=-caint --poweron-settle-ns 1000
python3 eda/pnr/run_postroute_parallel.py --parallel 2 --netlist FINAL_HIER_POSTPNR.v --sdf FINAL_TT_IO_GLS.sdf.gz --out eda/work/postroute-parallel-min --sdf-corner MINIMUM --xrun-arg=-caint --poweron-settle-ns 1000
```

调度器先调用冻结的 `run_postroute.py --dry-run` 准备完整 synthetic+dma 矩阵，此时只有 `PREPARED` 状态。随后生成仅改动一个时钟发生器区域的派生 TB，保存原始命令，只替换各用例的 TB 路径；固件和全部时序参数保持不变。实际执行原始 `xmsdfc` 命令及记录的仿真命令，持续核对输入及准备文件 SHA。每组用例自检和完整矩阵均复用原审计，全部通过后才可记录 `PASS`；只完成准备或部分用例不构成通过。

Xcelium 的 `-caint` 按综合网表中的无延时连续赋值 alias 处理互连，跟踪实际源驱动并注入对应 INTERCONNECT 延时。默认模式在跨越单向 `assign` 时退回目的 PORT 延时并报告 `SDFNCAP`；多个源的路径会共用最大的 PORT 延时，不能据此确认各源路径的延时正确。使用 `-caint` 前须核对相关 `assign` 无延时、目的信号确由该赋值驱动，并避免同时使用 `-intermod_path`。它改变互连注入方式，不屏蔽警告或关闭时序检查；正式运行仍拒绝 `SDFNCAP` 及其他 SDF/TIM/NDL 诊断。机制依据课程安装的 Xcelium 21.09 官方文档：`ElaboratorOptions/Verilog_Options.html` 的 `-caint` 小节及 `SDFAnnotation/Verilog_SDF_Annotation.html` 的连续赋值互连说明。

原始 SDF 的少量负 IOPATH 在 Xcelium 21.09 中可能无法完整补偿，`NDLFAL`、`NDLNOC`、`NDLPAR`、`NDLMLD` 均不能作为成功注入。正式 GLS 用 Innovus 的 `-filter` 将负传播延时归零，保留负 timing checks；这是明确的仿真模型近似，物理 setup/hold 仍以原始 STA 和实际提取报告验收。不要使用 `-target_application verilog` 预设：它还会重算 parallel arcs，不能视为仅负延时归零。有模型和信号引脚的 `ANTENNABWP7T` 保留在功能网表中；后仿准备逐条核对 SDF 的 CELL 与 INTERCONNECT 端点，拒绝 SDF/TIM/NDL 诊断。

已有冻结物理结果时，可用 `export_gls_sdf.tcl` 从最终检查点另行导出。设置 `CHIP_GLS_CHECKPOINT` 为完整 `.enc.dat` 目录、`CHIP_GLS_EVIDENCE` 为新的证据目录，在课程环境运行 `innovus -no_gui -init eda/pnr/export_gls_sdf.tcl`。入口将 config 的输入清单和所有新报告隔离到证据目录，保留恢复前后时钟、SDC、空 path-adjust 与 setup/hold 检查，生成 `restored_raw_1.sdf.gz`、`restored_raw_2.sdf.gz`、`filtered.sdf.gz`、`restored_raw_after.sdf.gz`。同会话三份 RAW 应除日期外一致；按 CELL、arc 条件与数值槽核对 filter 仅改变负 IOPATH 和负零，其他延时、互连和全部检查应保持。恢复后的 RAW 与原始冻结 RAW 的重新计算差异须单独记录。

`audit_physical.py` 核对真实 DEF/LEF/原生 IO GDS、PAD 端点守恒和最终物理连接；`audit_timing.py` 检查实际时序与物理报告。原生 IO 电源轨的几何连续性与核心 PG 的 special-routing 连通性分别验收。工艺原始视图保持外部授权目录，不入 Git。

`render_layout.py` 从实际 DEF/LEF 绘图，图片标注阶段与来源 SHA；它是物理数据库几何渲染，不仿造 EDA GUI 截图。独立 foundry DRC/LVS、IR/EM、全 PVT 和上板验证不由名义 TT 的课程 PNR/SDF 通过自动涵盖。

正式布线后验收使用 `--poweron-settle-ns 1000`：生成原测试台的派生副本，仅将系统时钟发生器延后 1000 ns，再保持 20 ns 周期；复位继续等待原来的 8 个下降沿，JTAG 仍为 100 ns。原 TB、RTL、固件及全部时序检查不改。初始时钟为 0 的 1000 ns 是明确的外部上电条件；原/实际命令、唯一改动区域 diff 和两个源文件哈希均保存。默认 0 保留旧刺激，不能把有启动违规的旧 MAX 运行算作通过。详见 [启动协议](../BOOT_PROTOCOL.md)。
