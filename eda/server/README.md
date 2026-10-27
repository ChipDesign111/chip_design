# 本上传版本：从解压到查看结果

版本目录：`{{UPLOAD}}`。源码提交：`{{COMMIT}}`。

状态：{{STATUS}}，完成 {{STEP}}/34。最终 Setup/Hold WNS：{{SETUP}} / {{HOLD}} ns。含 PAD 的整个 Die：{{AREA}} mm²，上限 {{AREA_LIMIT}} mm²。尚未生成不表示通过。

本版本为 INT8 64→32→6 完整 SoC：第一层 2 输入×32 输出、第二层 1×6，DMA 从主 SRAM 预取权重，两个 64 字节缓冲交替使用。整颗含 PAD 面积上限 3.8 mm²。双击本目录 README.html 阅读；各版本独立。

先读[当前设计数据流](../docs/当前设计数据流.md)理解本设计，再按以下阶段执行。

## 1．服务器解压和参数准备

在 SSH 登录后的 Bash 中执行（把版本名替换成上一步实际值）：

```bash
cd "{{UPLOAD}}"
bash ../../unpack.sh "$PWD"
cat configs/design.json
```

本次目录下的 deploy 是压缩包解出的源码；configs/design.json 是本版本可编辑配置。默认 PDK 为 /lec/pdk/tsmc180，宏资料来自 /lec/lab4，周期 20 ns，核数 8；核心请求 1648×1648 μm，四侧余量 150 μm，目标利用率 0.85，包含 PAD 的面积上限 3.8 mm²。


目标利用率0.85用于标准逻辑面积规划检查；固定核心边长1648µm才直接决定本轮外框。上一轮最终实测密度63.089%，并非规划参数0.68。新外框请求1948×1948µm（3.794704mm²），网格对齐后需核对≤3.8mm²；不把85%参数或含Filler密度当作实测逻辑密度。




rc_temperatures.tcl在创建及每次恢复数据库后，用Innovus原生get_rc_corner -T读回RC角25/125/0/−40°C，保存evidence/rc_temperatures.json；不一致便停止。Genus使用-temperature，Innovus使用-T，不能混用。旧版本曾只有库温度匹配、RC实际均25°C，是否包含此修正应看本版本源码和实际读回记录。

**第一次运行 check_env 前** 修改 configs/design.json。准备完成后 work 中的输入被固定，禁止修改来冒充续跑。更换参数请新建上传目录。1648+2×150=1948 μm 只是请求值；实际尺寸按工具网格对齐后的数据库和最终输出核对。

本版`insert_automatic_clock_gating=false`，让寄存器使能保留为数据选择逻辑，关闭Genus额外插入门控的优化；原RTL显式时钟结构不改。上一版的最终复位相位测试发现自动门控使能时序违规，因此本版重新映射并从头实施。时钟功耗或逻辑面积可能增加，须看本版真实结果，不复用旧版本的通过结论。

验收使用native_library_zero_slack：保留四个匹配库角、系统20ns、含PAD整颗≤3.8mm²。最终Setup/Hold均要求WNS≥0、TNS=0、违规路径数=0，电气检查遵守原生Liberty及讲义原SDC；不增加设计级边沿限制。default DRC、真实信号/核心供电连通及天线须通过，IO抽象限制按同源原生几何证据记录。只在真实负余量时修复Hold：先0目标，仍有残项时按讲义尝试0.02ns优化目标；0.02ns不是验收门槛。普通优化密度上限统一0.85，不再分83%/85%预算。详见[验收条件](../docs/验收条件.md)。

## 2．独立阶段一：环境检查

```bash
bash ./check_env.sh
```

check_env.sh 将本版本 RTL、EDA 程序、配置和授权宏视图复制到 work，形成输入快照，再检查 Genus、Innovus、Tcl/Python、PDK、宏视图和显示环境。生成 work/evidence/input_manifest.json、doctor.json 和 logs/environment.log。退出码必须为 0，才能继续。

文件作用：filelist.f 指明编译顺序；design.json 指定工艺、周期、面积及资源；宏的 .lib 给出延时和面积、LEF 给出外形及布线障碍、GDS 给出真实版图。没有匹配视图就无法完成对应阶段。

## 3．独立阶段二：综合和物理实现

```bash
bash ./run_eda.sh
```

Genus 将 RTL 变成当前工艺的门级网表；先检查 SRAM 恰好一个、CPU/NPU/DMA 没被错误裁掉、锁存器为零，再依据单元面积和 SRAM 障碍估算摆放空间。若规划容不下，或整个 Die 超过上限，流程停止，不能只把边框缩小强行通过。

Innovus 随后依次完成楼层规划、六个信号 PAD、四边 28 个供电/POC 单元、供电网格、标准单元摆放、时钟树、布线、修复和输出。每一步实际执行正文在 work/evidence/commands/NN，解释和结果在 work/evidence/运行报告.md，检查点在 work/pnr/my_soc_top/backup/stepNN.enc 及 .enc.dat。

允许整段脚本运行；它按讲义顺序执行并在每步审计，失败停止。分段学习时先 source ./run_env.sh，再调用 bash "$EDA_DEPLOY/server/bin/eda.sh" pnr --work "$EDA_WORK" --until N。未完成综合时先调用同入口的 synth；具体步骤见 34 步说明。不要在已有步骤 34 的工程从头覆盖运行。

默认保存 GUI 截图；无截图需求可用 bash ./run_eda.sh --headless。这个选项只跳过图片，仍然执行 EDA 检查。大型数据库不搬回本机。

## 4．独立阶段三：整理结果

```bash
bash ./collect_results.sh
```

此阶段重新核对最终输出、形成交付清单并压缩小型回传包。只有同一份输入的 34 步都成功，才能生成可回传状态。它不会把部分完成的工程写成成功。还可 bash ./run_all.sh 依次调用上述三个脚本；需要 SSH 断开后继续时，优先使用本机 remote.py run --detach。

## 5．找报告、判断是否达标

双击本版本 README.html，或执行：

```bash
cat results/summary.json
cat work/evidence/geometry.json
cat work/evidence/synthesis.json
cat work/evidence/step_33.json
cat work/evidence/step_34.json
```

先确认 pipeline_exit_code 为 0、last_completed_step 为 34，再确认以下项目：

| 关注点 | 文件及判断方法 |
| --- | --- |
| 整颗面积 | geometry.json 的 whole_die_area_mm2 和最终 LEF/DEF/GDS 的 Die 外框一致，且 ≤3.8；Genus cell_area 是单元面积，不能代替它 |
| 综合结构 | synthesis.json：一个原生主 SRAM，无不明叶子单元，latch_area 为零；CPU、NPU、DMA 层次存在 |
| 时序 | reports/postFiller 下分别看 Setup/Hold summary；WNS≥0、TNS=0、违例路径=0 |
| 电气规则 | Setup summary 的 max_cap、max_tran、max_fanout 的 real/total 均为 0；Hold 没该表时不能当作“自动为零” |
| 物理问题 | step_31/33 的真实 DRC、天线、普通信号连通；IO 抽象层例外必须有本轮原生电源轨几何证据 |
| 最终视图 | step_34 与 delivery_manifest：DEF、网表、SDC、SPEF、SDF、LEF、GDS 均生成且相互对应 |

若第33步的完整核心供电报告出现 dangling wire，表示电源线有超过有效连接点的多余尾段。正式脚本仅在第33步所有物理单元和Filler接入后用 `editTrim -nets {VDD VSS}` 修剪真实几何，再重新检查完整连通性、DRC和最终时序；没有排除悬线检查。更改脚本需要新上传版本，旧版本的冻结输入和失败报告保留。

WNS 是最差时间余量；负值表示至少有一条路径未达标。Setup 检查数据是否来得及，Hold 检查数据是否变化过早。SDF 是延时注释文件，**导出 SDF 不等于做过 SDF 后仿**；独立工艺 DRC/LVS、IR/EM 等结果也不能由本教学流程推断。完整分析见[报告查找与分析](../docs/报告查找与分析.md)。


## 6．本目录结构与文件作用

| 路径 | 作用 |
| --- | --- |
| chip_design_eda.tar.gz、.sha256、upload.json | 本次原包、校验值、上传身份 |
| deploy/rtl | 上传的当前硬件源码；CPU、AXI、NPU、DMA、启动和 SRAM 适配 |
| deploy/server | 正式 EDA 程序、Tcl、工艺路径配置，不包含 PDK |
| configs/design.json | 第一次环境准备前可调整的本版本配置 |
| check_env.sh、run_eda.sh、collect_results.sh | 三个独立阶段，依次运行 |
| run_all.sh | 顺序调用三个阶段；本身不包含另一个 EDA 实现 |
| run_env.sh | 本版本自己的绝对路径，供阶段脚本使用 |
| work/src、config、flow | 本轮冻结的源文件、参数、程序；不要修改 |
| work/syn/my_soc_top | 综合门级网表、约束、面积和时序报告 |
| work/pnr/my_soc_top/backup | 各步数据库与加载脚本，成套保留 |
| work/pnr/my_soc_top/reports | 摆放、时钟树及布线后时序报告 |
| work/pnr/my_soc_top/outputs/manual_final | 最终 GDS、DEF、网表、LEF、SDC、SDF、SPEF |
| work/evidence | 输入身份、每步记录、命令、截图和中文运行报告 |
| work/review_delivery.tar.gz | 校验后供本机抓取的轻量结果包 |
| logs | environment、flow、collect、pipeline 日志及退出码 |
| results/summary.json | 当前完成状态，优先查看 |
| docs | 本版本讲义对照、术语及结果分析说明 |

公用脚本只有 ../../unpack.sh。不同上传版本不共用 work 或结果。PDK 为只读外部依赖；Lab4 工程保留在根目录 lab4。

## 7．失败恢复与清理

先看 logs/pipeline.log 和本阶段日志。源码、配置没变的中断可以再次运行相应阶段；输入需要修改时，新建上传目录。不要删除数据库或改写 input_manifest 伪造续跑。

```bash
bash deploy/server/bin/eda.sh clean --work "$PWD/work" --dry-run
bash deploy/server/bin/eda.sh clean --work "$PWD/work"
```

默认保留本次原包及正常中间文件。清理器只处理约定的临时包/遗留交付包，不删除检查点与最终视图。完整步骤解释见 docs/讲义34步与文件对照.md。
