# 本上传版本：从解压到查看EDA结果

版本目录：`{{UPLOAD}}`

源码提交：`{{COMMIT}}`。状态：{{STATUS}}。后端完成{{STEP}}/34步，最终Setup/Hold WNS为{{SETUP}} / {{HOLD}} ns。尚未生成的指标不表示通过。

双击README.html可在服务器浏览器中阅读本指南。各上传目录拥有独立的原包、脚本、配置、work和结果；不使用其他上传版本的文件。

## 1．调用公共脚本解压

以下命令在服务器Bash中运行。进入本次存放压缩包的目录：

```bash
cd "{{UPLOAD}}"
bash ../../unpack.sh "$PWD"
```

unpack.sh核对原包SHA-256、归档路径及逐文件校验值，解压到本目录deploy，生成阶段入口、配置和本说明。SHA-256是文件内容的校验值，可发现传输损坏或内容变化。相同包可重复解压恢复入口；不同包必须放到另一个新上传目录。解压不会启动EDA。

若已有check_env.sh、run_eda.sh、collect_results.sh和run_env.sh，初始化已完成，可进入下一步。

## 2．环境检查与工程准备：check_env.sh

```bash
cat configs/design.json
bash ./check_env.sh
```

此脚本首次创建本版本work，复制RTL、正式EDA脚本和SRAM视图，冻结输入身份；随后检查Python、Genus、Innovus、PDK、宏视图和显示环境。PDK默认从/lec/pdk/tsmc180读取，SRAM资料从/lec/lab4读取。

如需修改工艺路径、周期、CPU数、宏坐标等，先编辑本版本configs/design.json，再首次运行check_env.sh。准备后输入被冻结；需要改变RTL、参数或实现脚本时，新建上传版本。再次执行check_env.sh仅检查已有工程，不覆盖它。

效果：生成work/evidence/doctor.json，控制台写入logs/environment.log。退出码0表示准备与环境检查成功；本步不做综合或功能仿真。

## 3．实际实现：run_eda.sh

```bash
bash ./run_eda.sh
```

此脚本先用Genus将RTL映射成工艺单元网表，再按本轮面积规划核心，最后执行Innovus讲义01–34步：导入、PAD和SRAM安排、供电、单元放置、时钟树、布线、时序及电气修复、最终检查和导出。

每步保存实际Tcl、检查JSON和数据库，讲解与本轮结果写入work/evidence/运行报告.md。入口日志为logs/flow.log；工具原文为work/evidence/genus_synthesis.log和innovus_*.log。

完成标志：退出码0、work/evidence/last_step.txt为34，step_33.json和step_34.json存在，且没有unexpected_tool_errors.json。仅生成部分文件不表示完成。再次执行在本版本work内继续进度。无显示且不需要截图时用bash ./run_eda.sh --headless。

## 4．报告与交付整理：collect_results.sh

```bash
bash ./collect_results.sh
```

此脚本不重新实现设计。它重建逐步报告、核对最终阶段、生成完整交付清单和包，再生成适合本机阅读的review_delivery.tar.gz、.sha256和review_manifest.json。控制台在logs/collect.log，本README和results/summary.json同步刷新。

完成标志：退出码0，上述三个文件在work中存在。小包包含报告、阶段结果、正式脚本、RTL、布局图及压缩层次网表。大型GDS/DEF/SDF/SPEF、平坦网表和数据库留在本版本服务器目录；清单记录其位置、大小及SHA。

## 5．一次连续执行三个独立阶段

run_all.sh只负责按顺序调用上述三个脚本，任何阶段失败就停止：

```bash
bash ./run_all.sh
```

长任务建议在tmux中运行，或在本版本目录后台启动：

```bash
nohup bash ./run_all.sh > logs/launcher.log 2>&1 < /dev/null &
```

总日志是logs/pipeline.log。整轮结束后生成logs/run_exit_code.txt，0表示三个阶段都成功。文件不存在时要结合日志和进程判断，不能认为已完成。同一版本不要并发启动两份任务；关闭本机窗口不停止服务器nohup任务。

## 6．查看和理解结果

- [逐步运行报告](work/evidence/运行报告.md)：每步是什么、为什么做、实际命令和实际结果。
- [第33步最终检查](work/evidence/step_33.json)：Setup/Hold、DRV、DRC、天线、放置、核心供电和信号连接。
- [第34步导出检查](work/evidence/step_34.json)：DEF端口、SDF实例、SPEF网络、GDS结构及引用关系。
- [最终时序原报告](work/pnr/my_soc_top/reports/postFiller/)：summary.gz为汇总，all.tarpt.gz为详细路径；压缩文本用gzip -cd 文件 | less阅读。
- [布局图](work/evidence/34_final_layout.gif)：观察外围、SRAM、核心逻辑及供电网格；headless时不生成。
- [最终导出目录](work/pnr/my_soc_top/outputs/manual_final/)：GDS为几何，DEF为布局布线，网表为单元连接，SDF为延时，SPEF为互连寄生。
- [报告分析方法](docs/报告查找与分析.md)、[基础知识](docs/基础知识.md)、[讲义34步](docs/讲义34步与文件对照.md)。

WNS是最差路径的时间余量，单位ns；Setup与Hold都应≥0，TNS及违规路径数应为0。DRV是负载、转换时间、扇出等电气约束违规，DRC是几何规则检查。已分类IO抽象限制如有保留，必须单独读，不能把原报告非零项写成零。

本流程为单TT、关闭SI的教学实现。功耗为无实际活动输入的估计；独立晶圆厂DRC/LVS、IR/EM/ESD、等价验证及SDF回标仿真不包含在这些结果中。

## 7．回传后在本机打开

回到Windows仓库根目录，用分支已有脚本抓取、校验和解压小包：

```powershell
python eda/remote.py fetch --upload "{{UPLOAD}}" --wait
```

--wait允许结果尚未生成时继续等待。命令打印本机结果目录，双击其中README.html或用编辑器打开README.md，再沿链接阅读core/evidence/运行报告.md和原始报告。需要指定位置时加--output '本机的空目录'。不必手写scp或解压命令。

## 8．文件结构和作用

| 路径 | 作用 |
| --- | --- |
| chip_design_eda.tar.gz、.sha256、upload.json | 本次原包、传输校验及解压来源；原包保留 |
| deploy/ | 本版本server、RTL、docs和source.json |
| configs/design.json | 首次准备前可编辑的本版本配置 |
| run_env.sh | 只指向本版本的变量，阶段脚本自动读取 |
| check_env.sh | 准备工程并检查环境 |
| run_eda.sh | 运行或继续综合及01–34步 |
| collect_results.sh | 整理、核对、打包结果 |
| run_all.sh | 依次调度上述三个独立阶段 |
| work/ | 全部输入快照、综合、后端、中间文件、检查点、原报告及最终导出 |
| logs/ | 各阶段、总调度和启动日志，以及退出码 |
| results/summary.json | 本版本进度与最终指标摘要 |
| docs/ | 详细说明、基础知识和报告分析 |
| README.md、README.html | 本版本文本与GUI操作指南 |

## 9．失败、继续和清理

先查看失败阶段的logs，再读work/evidence对应工具原文。缺工具或共享资料时修复环境后再执行check_env.sh；正常进度可用run_eda.sh继续。需改变冻结输入或存在未解决工具错误时，新建上传版本，不要删除错误记录强行推进。

回传校验成功后，如需清理交付压缩包，先预览：

```bash
bash deploy/server/bin/eda.sh clean --work "$PWD/work" --dry-run
```

核对列表后去掉--dry-run执行。只清理本版本交付包及已知暂存；保留原上传包、清单、日志、报告、中间文件、检查点和最终视图。清理后再次回传前，重新执行collect_results.sh。
