# EDA实际验证与完整运行结果

当前W8A4 SoC已实测完成讲义范围的综合、01–34物理实现与GDS导出。完整逐步命令、解释及结果见[运行报告](example_run_01_to_34.md)，机器记录见[physical_execution.json](physical_execution.json)与[汇总](validation.json)。

| 最终项目 | 实测结果 |
| --- | --- |
| 系统时钟周期 | 20 ns |
| 实际Die尺寸 | 3400.32 × 3400.32 um |
| Setup / Hold WNS | +0.710 / +0.015 ns |
| Setup / Hold TNS、违规路径 | 均为0 |
| 电气DRV Real / Total | 均为0 |
| default DRC、天线违规 | 均为0 |
| 完整核心VDD/VSS连通 | 无问题或警告 |
| 常规信号连通 | 未解决信号问题0；VDDPST/VSSPST两项库抽象限制由原生轨道、位置及拓扑证据单列 |
| 导出交叉核对 | 10物理端口；165244条非顶层SDF实例路径匹配；185556个SPEF网络；615个GDS结构，无未定义引用 |

这些数值取自填充后的第33步及第34步导出审计。分析使用单TT、SI关闭、原生低精度等级RC提取。未执行独立工艺DRC/LVS、IR/EM/ESD签核、功能等价验证或SDF回标仿真。常规信号报告的两项IO抽象限制没有改写成原始报告0问题。

## 分段执行与来源

| 执行部分 | 真实来源与复用方式 | 记录 |
| --- | --- | --- |
| 77份RTL展开 | Genus 19.17新运行，无未解析引用和空模块；其他警告保留 | [elaboration.json](elaboration.json) |
| 完整工艺映射 | 新运行得到165606个叶单元、唯一主SRAM、Latch面积0、Cell Area 4672791.309 um² | [synthesis_execution.json](synthesis_execution.json) |
| 01–31 | work_padfix实际执行；复用已核对同源RTL、规范化综合设置及库身份的综合网表 | [最初01–14验证](pnr_smoke.json)、完整运行报告 |
| 32–34 | work_fanoutfix从通过的第31步检查点继续，重新执行扇出ECO、时序修复、填充、最终检查及导出 | [检查点来源](checkpoint_seed.json)、physical_execution.json |
| IO原生几何复核 | 新工程重新核对原生库轨道；原阶段22的工具命令和输入身份保留 | [io_reaudit.json](io_reaudit.json) |

早期步骤保留原输入身份。导入工具逐项比较RTL字节、规范化综合/PNR设置和库身份，逐文件核对种子数据库；冻结输入清单保持原样。完整报告对继承结果和本工程新执行结果分别标记。开发工具为[综合网表复用](../tests/adopt_synthesis_fixture.py)和[物理检查点复用](../tests/adopt_physical_fixture.py)；普通用户按操作指南从RTL运行，不需要执行这些工具。

## 本次补齐的布线后扇出修复

原布线后分析有2个真实扇出违规，均为17负载超过库的16限制。已确认其中一条包含16个逻辑输入和一个布线阶段新增的天线二极管。工具日志明确说明普通postRoute优化跳过扇出修复，重复调用不能清零。

修正后的第32步读取当前明细，保留原天线二极管，每条网络插入一个BUFFD2BWP7T非反相缓冲器并分担8个逻辑输入。脚本核对所有原输入仍位于正确分支，再合法化、重新布线、提取RC和检查。实际分流记录在physical_execution.json的fanout_eco_splits，原限制和20 ns周期均未放宽。最终扇出、其余DRV、Setup/Hold、DRC及天线检查通过。

## 自动化与兼容性

| 检查 | 本次结果 |
| --- | --- |
| 仓库政策、文档链接、保留硬件 | 通过；75份保留硬件SHA未变，功能RTL未修改 |
| 控制与报告回归 | 38项通过：报告缺项/负零、Real/Total、IO证明过期、继承证据、扇出解析/分流、几何、打包等 |
| 服务器程序 | 8份Python源码符合3.8语法；Python 3.8.10实际执行控制和轻量收集；61份Tcl完整 |
| 准备与库检查 | 独立新工程通过，15份实际库/工艺文件身份固定 |
| 输入变化保护 | 临时修改被拒绝，精确恢复后正常 |
| 部署包 | 173项；不含PDK、厂商SRAM资料、数据集和旧EDA数据库 |

完整部署快照的逐文件SHA在[remote_compatibility.json](remote_compatibility.json)。实际执行的Python/Tcl/Shell/SDC与当前源文件逐字节核对；教学JSON和说明文档在实验后补充了解释。轻量收集工具另在最终结果上实际运行并校验归档内容。

既有功能基线位于test/2026-10-20/validation.json，部署核对其中86份RTL资料SHA；本次没有重新执行功能仿真。原Lab 4数据只作为[历史解析器样本](historical_parser_fixture.json)，没有用于补齐新SoC结果。

完整远端工程：`/home/s2400011041/eda_validation/20261020_eda_9d2c7f/work_fanoutfix`。大型物理/寄生视图及完整归档留远端；轻量包包含配置、源文件、gzip层次网表、阶段报告和实际命令，轻量包约19 MB，652项文件已在Windows解压并核对SHA，gzip层次网表的解压原文SHA也已核对。收集结果见[review_collection.json](review_collection.json)，完整文件索引见回传包review_manifest.json。
