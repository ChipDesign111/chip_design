# 完整 SoC 物理证据审计

`audit_physical.py` 仅读取文件，不启动 EDA，也不改 RTL、网表、约束或报告。它使用 Python 标准库；原生 IO GDS 几何检查额外需要 `gdstk`。没有原生 GDS 时结果为 `INCOMPLETE`，不会把遗漏检查当作通过。

```text
python eda/pnr/audit_physical.py --config <audit_inputs.json> --output <physical_audit.json>
```

以 `audit_config.example.json` 创建本次运行的配置，路径相对配置文件所在目录解析。不要把私有工艺内容提交仓库。`stage_artifacts` 的 SHA256 应来自已经完成的生产阶段 manifest，不能在审计失败后用新哈希掩盖文件变化。至少绑定综合输入、紧接 IO 插入的网表、最终物理网表和最终 DEF；可继续加入 RTL manifest、SDC、checkpoint 清单、CTS/hold 报告和 RC 提取文件。

严格的逐引脚守恒检查比较综合输入与 **IO 插入后、优化前** 的快照。这两份网表必须保留相同的核心实例层次和名称。如果导入 Innovus 即展平，先导出插 IO 前的同层次核心网表，作为配置中的 `pre_io_netlist`，同时把原综合网表及其 manifest 加入 `stage_artifacts`。最终网表允许 CTS、hold 修复和合法缓冲改变核心连接，改为核对 PAD、控制常量或 tie 驱动、物理电气绑定与旁路。

检查内容包括：

- 六个信号 PAD，五输入一输出，插入前后的原核心 pin 集合完全相同；最终 PAD 控制值正确，端口不能绕过 PAD。
- 唯一主 SRAM 的新层次 `i_mainmem/i_sram/i_macro`、真实 LEF 尺寸、固定状态、核心内 halo；所有 CORE 类单元的行、站点、方向、边界、宏间距和重叠。
- 从 DEF 的实际 DIEAREA 计算四边、四角与 filler 拼接，不依赖旧模板坐标、filler 数或标准单元数。每个普通 IO 都有恰好一个对齐 Bond PAD，预期覆盖与普通 IO 相互重叠分开处理。
- 六个信号和四个电源物理端口、DEF 的 PAD 两侧电气连接、LEF 声明的 PG pin 与 special net 绑定。
- 实际使用的各 IO/filler 原生 M4 轨贯通及 corner 转弯，再结合完整 DEF 拼接检查 IO 环几何连续。
- placement、核心 PG、信号连通和 Innovus route DRC 报告。若信号报告仅有明确允许的 `VDDPST/VSSPST` 原生轨无抽象布线两条，保留真实数量及范围；其他连通问题均失败。不能把它描述为零连通问题。
- 所有输入文件的实测哈希，与生产阶段冻结身份逐一比较。

`capture_physical.tcl` 可由主流程在已完成的阶段中 source，只采集当前 Innovus 数据库的只读元数据。设置 `PHYSICAL_AUDIT_DIR`，可选 `PHYSICAL_AUDIT_STAGE`。它不替代 DEF、网表、报告导出或生产 manifest。

这个审计不证明功能等价、setup/hold、时钟覆盖、后布线 SDF、foundry DRC/LVS、天线、ESD 或 IR/EM。CTS 和后布线必须另用实际 early/late 视图检查 setup 与 hold，包含新增负沿复位释放寄存器的半周期路径，保留修复前后报告及未约束路径证据。

## 后布线时序及报告独立审计

```text
python eda/pnr/audit_timing.py --pnr <本轮PNR输出目录> --out <审计JSON>
```

该脚本只用 Python 标准库，读取 `reports/final_setup/`、`reports/final_hold/` 下的 timeDesign summary（含 gzip），以及 `final_setup_paths.rpt`、`final_hold_paths.rpt`。检查完整汇总的 WNS/TNS、违例路径数、实际分析路径数，并核对有限详细路径样本的最差 slack 一致。报告原字段是 `Violating Paths`；只有它为零时才可推出违反端点为零，不能把非零路径数量误称为独立端点数。

最终 `outputs/my_soc_top.sdc` 必须保持 sys/JTAG/virtual 周期 20/100/1000 ns、sys/JTAG propagated、无物理源的 virtual ideal；两物理时钟的 setup/hold uncertainty 固定为 0.52/0.2 ns，virtual 保持 0.42/0.42 ns。导出的 path-adjust 文件不得含有效命令，最终 SDC 也不得含额外 path-adjust 命令。

同时核对 setup DRV 表、最终 DRC、三类连通报告、天线、welltap 和 placement 的正面证据，绑定每个输入的 SHA256 并在结束前复查未变化。`input_identity.json` 和成功 invocation 的 manifest/console 必须证明从 init 至 export 各阶段已完成、使用同一物理输入身份。缺文件、空报告、未知格式或尚未完成的阶段均为 `INCOMPLETE`，不是通过。

原生 IO 轨无抽象 routing、Bond/IO 预期覆盖仍会输出 `REQUIRES_GEOMETRY`，单独保留为 `INCOMPLETE`；必须与 `audit_physical.py` 的真实几何结果联合解释，不能把它们改写为零 PG/placement 问题。这个时序报告审计不会自动把另一份审计的 PASS 合并成完整签核结论。
