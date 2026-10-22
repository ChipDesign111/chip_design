# W8A4 SoC 实测 EDA 结果与分析

这里保存已完成实验的正常EDA结果、原始报告和解释。没有开发单元测试、兼容性试验或临时工具。当前部署目录结构整理后，以下历史实测值保持原样，不把整理目录当作一次新的全流程执行。

| 项目 | 实测结果 | 对应文件 |
| --- | --- | --- |
| 系统周期 | 20 ns，50 MHz | summary.json |
| 工艺映射 | 165606个末级实例，1个主SRAM，无非预期数据Latch面积 | synthesis.json、reports/synthesis/area.rpt |
| 综合单元面积 | 4672791.309 μm² | reports/synthesis/area.rpt |
| 裸片尺寸 | 3400.32 × 3400.32 μm | geometry.json |
| 最终Setup/Hold WNS | +0.710 / +0.015 ns | reports/final/setup.summary、hold.summary |
| Setup/Hold TNS及违规路径 | 均为0 | 同上 |
| 电气DRV Real/Total | 均为0 | reports/final/setup.summary |
| 默认DRC、天线违规 | 均为0 | reports/final/drc.rpt、antenna.rpt |
| 完整核心供电 | 无问题或警告 | reports/final/pg.rpt |
| 信号连接 | 未解决信号问题0；VDDPST/VSSPST两项IO抽象限制分类保留 | reports/final/signal.rpt、step_33.json |
| 导出核对 | 10端口，165244条非顶层SDF实例匹配，185556个SPEF网络，615个GDS结构，无未定义引用 | step_34.json |

## 从哪个文件开始看

- [逐步实测运行报告](run_01_to_34.md)：01–34每步实际命令、说明与结果，明确标注分段来源。
- [结果汇总](summary.json)：指标、运行来源、各原报告的位置与SHA。
- [最终阶段结果](step_33.json)、[导出结果](step_34.json)：机器记录的验收项目及对应报告。
- `reports/synthesis/`：面积、QoR、门控、综合关键路径和估计功耗。
- `reports/final/`：填充后的Setup/Hold汇总、详细路径、放置、DRC、供电、信号与天线报告。
- [布局图](layout.gif)：观察外围、主SRAM、逻辑及供电网格。

时间报告由原gzip文件解压为普通文本，内容未改；summary.json同时记录原压缩文件与当前文本的SHA。其他原始报告和阶段JSON直接保留。报告中的绝对路径指向当时服务器工程，不是当前仓库路径；在分支内按上述相对路径打开。

## 这些结果说明什么

完整SoC在本次单TT、SI关闭、原生low RC场景下，最终Setup/Hold、报告列出的电气限制以及工具内几何/天线/核心供电检查满足要求。Setup余量为710 ps，Hold余量15 ps，后者余量较小；不能据此推定其他工艺角也满足。

最终第一条Setup路径从NPU `core/mult_reg[1]/Q` 到 `core/hb_reg[1][16]/D`。Required为21.427 ns，Arrival为20.717 ns，余量为0.710 ns。Required包含时钟、建立时间及不确定度的调整；不能仅看Arrival超过20 ns就判失败。详细读法见[报告查找与分析](../docs/报告查找与分析.md)。

布线后曾有两个网络的负载17超过限制16。其中一条由16个逻辑输入加新增天线二极管构成。第32步保留二极管，每条插一个非反相BUFFD2BWP7T缓冲器并分担8个逻辑输入，重新布线/提取/分析后清零；20 ns周期和负载限制没有放宽。当前正式脚本仍根据本轮报告决定是否需要同类修复。

信号原报告仍有VDDPST/VSSPST两项no routing，涉及IO库抽象未完整表达原生轨道。分类依据是原生轨、角部、实际外围连续及四网拓扑证据；正确表述是“未解决信号问题为0，两项IO抽象限制分类”，不能把原报告写成0问题。

功耗为未加载实际负载活动的vectorless估计，不是推理实测功耗。独立晶圆厂DRC/LVS、IR/EM/ESD、功能等价和SDF回标仿真未执行。

## 实际执行来源

| 部分 | 来源 |
| --- | --- |
| 综合 | work03真实执行Genus综合，目标为同源的77份RTL |
| 01–31 | work_padfix实际执行，使用已核对同源输入的综合网表 |
| 32–34 | work_fanoutfix从已通过31的数据库继续，实际完成扇出/时间修复、填充、最终检查及导出 |

早期阶段保留原输入身份，没有把继承记录改写成重新执行。完整最终工程为 `/home/s2400011041/eda_validation/20261020_eda_9d2c7f/work_fanoutfix`。大型GDS/DEF/SDF/SPEF、平坦网表和完整数据库留服务器，原本地核心包在 `advanced_chip_study/lab4/xzx_rtl_20261020_final`。本分支只保留适合直接阅读的结果。

重新实验请从[操作指南](../docs/操作指南.md)开始；不要用此处静态JSON推进新工程进度。
