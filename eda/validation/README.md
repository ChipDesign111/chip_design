# EDA工具验证范围

本目录记录新增部署、控制程序和实际工具运行；汇总见[validation.json](validation.json)，实际命令与每步结果示例见[01–14运行报告](example_run_01_to_14.md)。脚本可执行与新SoC已完成物理实现是两项不同结论。

| 检查 | 本次实际结果 | 证据 |
| --- | --- | --- |
| 仓库政策、文档链接与保留硬件 | 通过；75份外围硬件SHA保持一致，功能RTL未改动 | tools/project.py check、validation.json |
| 自动化回归 | 29项通过，覆盖失败报告、时序表格、IO例外边界、端口拆分换网、几何生成、报告归档、部署包和大文件保留 | eda/tests/test_flow.py |
| Python兼容性 | 7份服务器Python源码符合3.8语法；服务器3.8.10实际执行准备、检查与控制验证 | [remote_compatibility.json](remote_compatibility.json) |
| 服务器环境和库 | 新目录准备通过；60份Tcl完整；实际15份库/工艺文件身份已固定 | remote_compatibility.json及远端evidence/doctor.json |
| 输入变化保护 | 临时修改被拒绝；精确恢复后正常，测试使用独立空闲工程 | remote_compatibility.json |
| 新SoC展开 | 77份RTL，Genus 19.17实际展开完成，无未解析引用、无空模块；警告保留 | [elaboration.json](elaboration.json) |
| 新SoC完整综合 | 通过映射及交接核对；165606个叶单元、唯一主SRAM、Latch面积0，Cell Area 4672791.309 um²；核心估算3100 um | [synthesis_execution.json](synthesis_execution.json) |
| 新SoC后端01–14与续跑 | 当前执行代码实际完成01–13，退出进程后从13恢复并完成14；实际Die 3400.32×3400.32 um，六路端点及十个物理端口核对通过 | [pnr_smoke.json](pnr_smoke.json) |
| 原Lab 4报告解析 | 真实旧报告及导出用于测试解析器；不是新SoC实现结果 | [historical_parser_fixture.json](historical_parser_fixture.json) |

既有功能证据位于test/2026-10-20/validation.json。部署打包核对其中86份RTL资料的SHA，作为同源既有基线；这次EDA资料提交没有重新执行功能仿真，不将既有PASS改写为本次新仿真。

真实商业EDA验证使用准备时固定的控制程序快照，其SHA和远端路径分别保存在记录中。最终控制程序另做新目录兼容性验证；不将较早快照的工具运行冒称为最终全部脚本的端到端验收。新SoC完整01–34、独立工艺DRC/LVS、IR/EM/ESD及SDF回标仿真未经完成时均不标为通过。

本次后端验证复用已经实际完成的同源综合结果：开发助手[adopt_synthesis_fixture.py](../tests/adopt_synthesis_fixture.py)逐项比较RTL字节、规范化综合配置及库身份，在新工程记录引用来源；没有修改输入清单，也没有声称目标工程重新执行了Genus。普通复现实验仍按操作指南从头综合。首次第08步发现端口拆分会更换内部网络，已修正为稳定内部引脚查询并加入回归；恢复检查点也已改为读取工具生成的.enc加载脚本。修正后代码经过上述真实01–14和跨进程恢复验证。

后端烟雾测试快照与最终部署的全部Python/Tcl/Shell/SDC执行文件逐字节一致；只有第08步教学JSON文字在测试启动后补充了引脚定位的说明。最终完整部署文件另在新准备工程执行了兼容性验证，逐文件SHA保存在remote_compatibility.json。15–34尚未进行本轮实际验证，不能把原Lab 4的最终结果用于补齐。
