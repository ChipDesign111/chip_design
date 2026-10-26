# 完整SoC SDF后仿：与现有main结果对比

2026-10-26，在原3.7956390976mm²物理结果上完成新的完整SoC后仿。**16组MAXIMUM SDF运行及1组无SDF门级对照全部通过功能自检；回标error、缺失实例和缺失时序检查均为0。** 16组工作窗口动态违规均为0；每组仍有9条初始复位和1条最终复位事件，19条负IOPATH仍被VCS截零，不能报告成全程零违规或无损签核。

## 1．结果入口与复现

先读本页，再按仓库eda/docs/后仿真操作指南.md操作。三个本机命令分别启动、查询和校验回传：

```powershell
python eda/postsim.py run
python eda/postsim.py status
python eda/postsim.py fetch --output C:/Users/zixiang/OneDrive/Desktop/advanced_chip_study/lab4/postsim_新目录
```

| 文件 | 内容 |
| --- | --- |
| [comparison.json](comparison.json) | 本次、旧main、物理结果、覆盖范围及来源 |
| [audit.json](audit.json) | 回标告警分类、16组逐条动态事件与窗口 |
| [input_manifest.json](input_manifest.json) | 原版图网表/SDF、原生库、仿真视图、SRAM适配副本及每个固件的SHA |
| [results.json](results.json) | 全部17个运行的功能、性能和消息数 |
| [SDF代表日志](sdf_max.log) | 全程启用timing check与notifier的原文 |
| [无SDF对照](gate_zero.log) | 独立编译、显式关闭时序检查的功能对照 |
| [负IOPATH清单](negative_iopath_inventory.json) | 19个原SDF行号及实际语句，没有改写原SDF |
| [全部轻量原报告](review_reports.tar.gz) | 65个逐文件校验的编译命令、日志、各样本日志、输入及审核文件 |

原main报告保留于eda/results/postsim_20261026及postsim_20261026.md，没有覆盖。

## 2．与现有main比较

| 项目 | main现有记录c9d7c5e | 本次e7852dc运行 |
| --- | --- | --- |
| SDF功能自检 | PASS，单组3659观测拍 | 16组PASS，均3658观测拍 |
| 无SDF同台门级对照 | 未提供 | PASS，3658拍 |
| 回标error | 41,098 | 0 |
| 回标warning | 报告13,581 | 3,342个告警标记，分类见下文 |
| 缺失实例/检查 | 原报告有层次、二极管、removal匹配问题 | 均0 |
| 原生NTC/RECREM及负检查 | 原报告注明未启用，部分负值被置0 | 已启用，负setuphold/recrem值保留 |
| 全程动态违规 | 代表组14条，复位阶段 | 每组10条：初始9、最终1 |
| 正常工作窗口 | 原有窗口控制对照0条 | 每组0条，全程没有关闭消息/notifier |
| 工作负载 | 原报告提供原自检样例 | 12组训练双样本+4组随机双样本，共32条输入 |
| 含PAD整颗面积 | 既有3.7956390976mm² | 不变，未做物理ECO |
| 静态Setup/Hold | +0.226/+0.019ns | 不变，引用同一物理实现，不是重新计算 |
| 功耗 | 35.3843mW，原功耗报告 | 未重新进行相同活动条件的功耗分析，不作差值结论 |

3658与3659的差异涉及测试平台的响应/完成采样定义，不能当作硬件加速一拍。当前平台在下降沿之后1ns读取完成标志，避免同一仿真时间槽的采样竞争；同台无SDF和SDF的观测计数完全相同。内部硬件NPU批次计数1035拍，也完全相同。

两版回标模型和测试平台配置不同，因此14条变10条不等于修复了4条电路违规。旧报告原始执行文件和测试平台位于另一账号/环境，本次未获得原文件来逐字重放；旧报告网表和未压缩SDF的SHA与本次输入不同。旧数值作为已有报告对照，**严格同输入对照是本次gate_zero与sdf_max**。

Cell+Net=2,552,370.657是原综合报告的库面积估计口径，不能替代含PAD裸片3.7956390976mm²。本轮不改硬件，不能把后仿通过说成面积进一步降低。旧功耗没有相同的后仿活动输入证据，所以不声称本次重新测得35.3843mW。

## 3．这次实际修正了哪些回标问题

1. VCS使用原标准单元模型的NTC与RECREM分支，编译使用neg_tchk和negdelay，保留负setuphold及recovery/removal检查。原模型/工艺库没有全局改动。
2. 从原step34物理数据库只读重新导出仿真网表，保留12个真实ANTENNABWP7T二极管。原教学交付网表省略了它们，使SDF互连端点缺失。导出脚本没有进行ECO，也没有重新摆放或布线。
3. 原SRAM模型只有正边沿period声明，SDF还要求负边沿period。服务器私有模型副本只补齐这条声明，复用原NOT_CLK_PER，数值仍由原SDF填入；不是删除或放宽检查。授权模型副本不提交、不回传。
4. VCS会在编译/展开阶段预处理常量sdf_annotate文件，所以编译目录提前放好原SDF。回标原文在build/sdf.log，不只看运行时打印的ANNOTATION_CALLED。

PAD后核心时钟边沿在SDF运行中为10.640、30.640、50.640、70.640ns，无SDF对照为10、30、50、70ns。这给出了延时实际生效的观测证据，不是仅调用函数后宣布成功。

## 4．剩余告警和时序事件

| 告警类别 | 数量 | 实际含义 |
| --- | --- | --- |
| SDFCOM_SWC | 2267 | 不是简单导线连接；VCS明确仍回标延时 |
| SDFCOM_IWSBA | 1055 | 层次互连结构提示；VCS明确仍回标 |
| SDFCOM_UHICD | 1 | 输出PAD到顶层目的端的上层互连特殊处理，DEVICE延时应用在PAD |
| SDFCOM_NIOD | 19 | 负单元IOPATH无法按原值处理，被VCS截0；保留完整对象清单 |

工具主回标汇总为3323条warning，随后延时处理阶段另有19条NIOD；因此按告警标记统计总数3342，不能只报主汇总而漏掉19条。回标error=0、实例/检查均匹配，不等于所有延时数值都无损支持。没有修改原SDF来掩盖这些限制。

每组ACTIVE_START=600ns，ACTIVE_END=238840ns。窗口包含完整SRAM装载、错误/部分启动测试、CPU执行、DMA和NPU自检及统计回读。窗口仅用于事后分类，没有关闭时序消息或notifier。

每组9条初始复位事件约在11ns附近，包括门控时钟/扫描选择检查；最终1条为复位重断言后SRAM地址的setuphold检查。audit.json逐项记录对象、时间和原始限值。所有16组均保留这10条，共160条复位阶段消息；工作窗口共0条。不能由正常工作0条推论异步复位所有相位都无电气风险，也未证明每个事件的物理根因。

## 5．功能结果与性能口径

第一层2输入×32输出，第二层1×6，合计70个INT8乘法器；偏置、累加和分数INT32，主8KiB SRAM及两个64B tile缓冲未改。当前RTL的84项哈希仍与已验证设计一致。

测试从Debug SBA请求边界发起真实AXI装载，不直接改SRAM数组，不强制CPU计算结果。CPU固件逐值比较两条样本的隐藏值、六个分数和类别，并核对64个tile及两级MAC发射次数。16组分别使用完整镜像重新启动，覆盖24条训练输入和8条随机输入。

所有组内部NPU批次计数1035，20ns下对应一批两条样本约20.7µs，包含等待权重，不包含主机镜像下载和CPU配置开销。实际DMA/MAC任一握手重叠93拍，读重叠62拍，写重叠93拍。3658拍是测试平台在启动提交响应之后的观察值，包含CPU软件开销，不是纯NPU延迟。

部分装载、错密钥和密钥单独写入不能放行CPU；完整2048字顺序覆盖后显式提交才执行。复位释放余量检查通过；最终重新断言复位撤销启动权限。测试没有掩盖复位期间的时序消息。

## 6．来源与文件结构

物理输入来自20261023_225536_e15483c，后仿程序版本e7852dc（基于现有main c9d7c5e），正式上传时源码干净。新目录：

```text
/home/s2400011041/Desktop/fullstack_chipdesign/uploads/20261026_193037_postsim_e7852dc
├── chip_design_eda.tar.gz、upload.json  上传原包与身份
├── deploy/server/postsim/             正式运行、导出、采集与测试平台
├── configs/firmware*.hex              16组固件/权重/输入/黄金值
├── logs/postsim.log                   总控与失败信息
└── postsim/
    ├── input_manifest.json           原输入和实际仿真输入SHA
    ├── inputs/                       大网表、原SDF、私有SRAM适配模型
    ├── build/、build_zero/            SDF/无SDF可执行程序及编译数据库
    ├── sdf_max/、sdf_firmware_*/      各SDF组原始日志
    ├── gate_zero/                    无SDF功能对照
    ├── results.json、audit.json       功能和时序/回标提取结果
    └── review.tar.gz、review_manifest.json  65文件校验回传包
```

本机完整轻量报告在 `C:/Users/zixiang/OneDrive/Desktop/advanced_chip_study/lab4/postsim_e7852dc_20261026`，从README.html进入。大网表/SDF、可执行文件、编译数据库和授权模型仅留对应服务器目录；旧物理work和旧main报告保持不变。

## 7．结论边界

本次比现有main记录补齐了实例与时序检查匹配、负时序检查支持和32条输入的完整SoC动态验证；功能自检全部通过，工作窗口未报告动态违规。仍有复位事件及19条负IOPATH截零，结论应写为“功能通过、工作窗口检查通过，并存在已列出的仿真限制”。

这是TT/1.8V/25°C、MAXIMUM SDF的一组有限激励验证；不是最小延时/多PVT、独立晶圆厂DRC/LVS、IR/EM/ESD或形式等价签核，也不是重新计算了面积、WNS和活动功耗。
