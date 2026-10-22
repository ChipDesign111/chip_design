# 完整 SoC 物理实现记录

2026-10-21，完整 SoC 已完成 Innovus route / finish / export、静态物理验收和约束覆盖分类，**布线后 SDF 动态验收已 PASS**：采用明确的 1000 ns 先复位后起钟协议，MAX/MIN 的自测和 DMA 共四个完整场景各完成两次启动、2048 字下载及回读，全部原始时序诊断为 0。静态检查的 PASS 不代替动态后仿。

输入固定为 GitHub `52be8c57b365b70536500526a52905352e505666` 加已验证的启动/复位集成修改。综合网表 SHA-256 为 `0ae65d8bf555fbd8214116300dd45670f627eb0bf4f2241e9f284baf844d3a67`；输入 SDC 为 `05d3373b7530e1f1e78b0f6ccde61afb0ce641b43709d659034c532058ceec78`。前序验收见 [综合结果](../RESULTS.md)。

运行目录为课程服务器 `eda/work/pnr-20261021-3400`。每段保留独立 invocation、日志、源码哈希、数据库和 Tcl 上下文。

| 阶段 | 最终状态 |
| --- | --- |
| 完整网表与物理视图导入 | 完成，0 tool errors |
| Floorplan / SRAM | 完成，实际 Die 3400.32 μm，core `{150.08 150.08 3250.24 3250.24}` |
| IO / Bond / filler | 完成，6 信号 PAD、28 供电 PAD、4 corner、34 Bond，功能叶端点守恒及四边 abutment 通过 |
| 电源构建与收尾 | 完成，核心 PG clean，PG stub trim 剩余项 0；原生 IO rail 单独几何验收通过 |
| 标准单元布局 / CTS | 完成，最终未放置实例 0；时钟插入、布线和最终优化已执行 |
| Route / finish / export | 完成，最终阶段 0 tool errors，最终布线 DRC 0、独立 VPA 违规 0、天线违规 0 |
| 最终静态 setup | WNS **+1.217 ns**，TNS 0，违反端点 0 |
| 最终静态 hold | WNS **+0.018 ns**，TNS 0，违反端点 0 |
| 最终 DRV | 0 |
| 独立连接/几何/身份审计 | **8/8 PASS**，包括实际 DEF、网表、LEF、原生 IO GDS 与工具报告 |
| 静态约束覆盖分类 | **PASS_WITH_EXPLICIT_CLASSIFICATION**，原 3138/3220 个未测试项保留并逐项解释，没有新增例外 |
| 布线后 SDF 动态验证 | **PASS**：1000 ns 上电协议下 MAX/MIN 四个完整场景通过实际日志和独立审计 |

静态结果使用课程 TSMC180 TT、1.8 V、25 °C 和原 20 ns 系统时钟、100 ns JTAG 时钟、1000 ns 虚拟时钟约束，不是多 PVT 收敛或 foundry 签核。

SRAM 实际 bbox 为 `{250.08 1338.235 804.675 2062.085}`。请求的 26 μm halo 经工具对齐后，实际外框为 `{229.2 1315.6 825.84 2085.28}`，最小间隙约 20.88 μm，覆盖 20 μm 宏电源环包络；最终以数据库和审计为准。

最终实例共 **565,775** 个，全部已放置：

| 分类 | 数量 |
| --- | ---: |
| 逻辑标准单元，含时钟/优化单元 | 175,354 |
| Core filler / tap | 388,216 |
| 主 SRAM | 1 |
| 信号 PAD | 6 |
| 供电 PAD | 28 |
| Bond | 34 |
| IO filler | 2,132 |
| Corner | 4 |

填充单元计入最终实例和几何占用，不能据此把填充后的占用率当作逻辑布局利用率。真实最终 DEF 的布局/布线预览已生成在私有 `preview/soc-postroute-layout.png`，对应 DEF 和 LEF 身份保存在同名 JSON 中；没有公开工艺库原文件或合并 GDS。

最终 DEF/LEF 的放置矩形面积逐实例求和如下；这是物理矩形面积，不是新的 Liberty 综合面积或功耗估计。Die 为 **11.562176 mm²**，core 为 **9.610992 mm²**。

| 项目 | 面积（mm²） |
| --- | ---: |
| 逻辑标准单元，排除 filler/tap | 4.336111 |
| 主 SRAM | 0.401444 |
| 逻辑加主 SRAM，排除 filler/tap | 4.737554 |
| 其中 NPU 层次逻辑 | 3.454171 |
| 其中 CPU 层次逻辑 | 0.354738 |
| 其中 DMA 层次逻辑 | 0.059433 |

NPU 等层次面积按最终实例路径归属；顶层新增 CTS/优化单元单列，未强行摊入 NPU。原始 LEF、最终 DEF 及审计解析器哈希和精确十进制累计保存在私有 `final-placement-area.json`。

## 独立物理证据

`audit_physical.py` 对本轮最终导出数据的 8 项检查全部通过，结果保存在 `eda/work/pnr-20261021-3400/physical_audit_fixed.json`；早期解析缺口产生的 `physical_audit.json` 保留为原始 FAIL 记录。检查包含 PAD 插入前后叶连接守恒、最终 PAD 控制与无外部绕接、core/row/site/方向/重叠及 SRAM halo、IO/Bond 几何、DEF 与网表供电绑定、原生 IO GDS 供电轨连续性、工具报告和跨阶段哈希。审计器的 30 项正反回归通过。

IO 插入阶段严格保留 1,458 个系统时钟叶端点、22 个 JTAG 时钟叶端点，其余四个功能脚各一个；工具新增或改名的层次 formal 通过真实物理叶端点追踪处理，不直接豁免。一个真实 SRAM 宏仍位于 `i_mainmem/i_sram/i_macro`；天线 LEF 叠加不覆盖基础 CLASS/尺寸/POWER 信息，只有指定的 Bond master 从核心宏计数中排除，并另做覆盖几何检查。

原始连通报告仍保留 **2 项原生 IO 供电 no-routing 提示**，placement 报告仍保留 **34 处预期 Bond/PAD 覆盖**。前者由原生 IO GDS 轨连续性及 DEF/最终 HDL 同网绑定提供证据，后者由指定 Bond 与对应 PAD 的实际几何匹配提供证据；没有删除原始提示或将所有 IO 电源问题统一豁免。显式供电脚检查共 28 个，其中 VDDPST 8 个、VSSPST 4 个。

## 静态约束覆盖

最终 `check_timing -verbose` 的 **3,138 个未约束端点提示**原样保留：CDN 1,830、SDN 24、TE 1,047、D 232、E 5。独立核对实际网表、单元模型、Liberty、原 SDC 和最终数据库的 late/early 查询后，覆盖分类为 `PASS_WITH_EXPLICIT_CLASSIFICATION`。这表示每项均有具体原因，不把未测试项改写为零或视为测得正裕量。

| 检查 | 满足 | 违反 | 未测试 |
| --- | ---: | ---: | ---: |
| Setup | 46,636 | 0 | 232 |
| Hold | 46,554 | 0 | 314 |
| Recovery | 15,222 | 0 | 1,854 |
| Removal | 15,222 | 0 | 1,854 |
| Clock gating setup / hold，各自 | 1,042 | 0 | 1,052 |

Late 共 3,138 项未测试，early 共 3,220 项。常量 D/E/TE、关闭 ICG 分支和既有全局异步复位例外均按精确引脚核对；116 个内部生成复位端点在 recovery 和 removal 报告中均明确为 `const`，同时匹配实际常量禁弧记录，没有假设 Liberty 存在 D 条件。额外的 82 条 hold 未测试项（81 个 D、1 个 SI）均逐项沿真实连接匹配原 `__coll_2` CDC hold-through 例外的 237 个选定引脚，零未匹配。

两个模式均没有无法解释的 `unknown`、`no_endpoint_clock`、`no_startpoint_clock` 或 `user_disable` 原因。恢复后的全部 34 条有效 SDC 命令与原最终导出一致，没有新增 false path、case analysis 或 timing-disable。完整私有证据为 `constraint-coverage-audit.json`；原报告中的理想虚拟时钟、五个 no-drive 和异步复位 no-input-delay 提示也保留，五个输入均已有 0.5 ns slew 模型。此分类不代替异步复位/RDC 或其他模式签核。

## 布线后 SDF 动态验证

当前状态为 **PASS**，仅适用于下述明确的外部上电协议。原始 SDF 保留；用于仿真的同会话 raw 导出与原始 SDF 对照，仅 38 个 CELL 内存在不超过 1 ps 的数值差异。仿真派生 SDF 只修正 18 条 IOPATH 中的 46 个负延时分量，另归一化 5 个 signed-zero，共 19 条 IOPATH 记录变化；**63,129 条含负值的 timing-check 记录保留**，时序检查继续启用，原始 STA 结果没有被替换。

最初直接使用 raw SDF 的仿真中止记录保留，不计为通过；会引入 285 ps 数值变化的 Verilog preset 导出未被采用。随后 MAX 基线的软件两次启动虽完成，但最初约 12 ns 有 3 条上电时序违规：一条 ICG E setup、两条 SE setup，严格验收为 **FAIL**。旧 MIN 两套完整场景的通过记录单独保留，不能据此覆盖 MAX 失败。

新一轮仅派生测试台的一个时钟发生器区域：上电时复位有效，系统时钟保持低 1000 ns，随后恢复原 20 ns 时钟；第一个上升沿为 1010 ns，原八个下降沿后的外部复位释放相应为 1160 ns。原测试台、RTL、固件和相对 JTAG/复位流程不变，全部 specify 和 timing checks 保持开启。MAX/MIN 的 5000 ns 启动 smoke 已无违规，但短 smoke 不包含完整下载和两次软件启动，不能作为完整后仿 PASS。正式 MAX/MIN 四个完整场景均已实际 **PASS**（每场景两次启动、2048 字下载及回读、0 条时序诊断），见 [启动协议](../BOOT_PROTOCOL.md)。

该结果只验证上述外部启动条件。如果产品要求系统时钟从上电开始自由运行，还需相应的复位/时钟门控初始化设计保障和重新验证。本轮分别核对了最终实际网表/模型/SDF 身份、注入诊断、完整测试完成标记及 timing violations，才验收动态终态；综合后 SDF 的既有 PASS 不能代替本阶段。

物理脚本兼容修复没有修改 RTL。库 LEF 的天线属性和超出六金属的宏抽象提示保留为材料范围限制；当前检查不代替独立 LVS、foundry DRC、IR/EM、ESD、形式等价或全 PVT 签核。


<!-- FINAL_PNR_CASES_BEGIN -->

### 四个正式动态场景的实际证据

| Corner | 固件 | CPU 启动 | 下载/回读字数 | 时序诊断 | 实际耗时（s） | case 审计 SHA-256（规范 JSON） |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| MAXIMUM | dma | 2 | 2048 / 2048 | 0 | 2194.723 | `7928ebc343d7bcbb8e9e26c809ba52fc07a174719ac67601051f92af2f6ef03f` |
| MAXIMUM | synthetic | 2 | 2048 / 2048 | 0 | 2151.718 | `28e31b7665812cad59834f381e59c89a602c22d11abf4e42e0c0f3d7b4f3ff8e` |
| MINIMUM | dma | 2 | 2048 / 2048 | 0 | 2186.701 | `7928ebc343d7bcbb8e9e26c809ba52fc07a174719ac67601051f92af2f6ef03f` |
| MINIMUM | synthetic | 2 | 2048 / 2048 | 0 | 2187.337 | `28e31b7665812cad59834f381e59c89a602c22d11abf4e42e0c0f3d7b4f3ff8e` |

原始注入统计如下。分母为模型全部潜在 specify 对象，不能据此声明源 SDF 端点覆盖率。

`MAXIMUM / dma`：

```text
		 No. of Pathdelays = 1737175 	 No. of Disabled Pathdelays = 0        Annotated = 100.00% (1737175/1737175) 
		 No. of Tchecks    = 214543  	 No. of Disabled Tchecks    = 0        Annotated = 100.00% (214543/214543) 
```

`MAXIMUM / synthetic`：

```text
		 No. of Pathdelays = 1737175 	 No. of Disabled Pathdelays = 0        Annotated = 100.00% (1737175/1737175) 
		 No. of Tchecks    = 214543  	 No. of Disabled Tchecks    = 0        Annotated = 100.00% (214543/214543) 
```

`MINIMUM / dma`：

```text
		 No. of Pathdelays = 1737175 	 No. of Disabled Pathdelays = 0        Annotated = 100.00% (1737175/1737175) 
		 No. of Tchecks    = 214543  	 No. of Disabled Tchecks    = 0        Annotated = 100.00% (214543/214543) 
```

`MINIMUM / synthetic`：

```text
		 No. of Pathdelays = 1737175 	 No. of Disabled Pathdelays = 0        Annotated = 100.00% (1737175/1737175) 
		 No. of Tchecks    = 214543  	 No. of Disabled Tchecks    = 0        Annotated = 100.00% (214543/214543) 
```

原始完成标记、两次 benchmark 指标、实际命令/输入身份及对应文件哈希保存在[机器摘要](../../test/2026-10-21/pnr/summary.json)。DMA 的 metric 3 是累计 DMA 忙周期。

<!-- FINAL_PNR_CASES_END -->
