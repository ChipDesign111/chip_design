# SRAM复位修正：SDF后仿与main对比

源码5191064的新物理数据库已完成34步与三个阶段，含PAD **3.7956390976mm²**，全局Setup/Hold **+0.371/+0.019ns**。由该数据库导出的匹配网表和原SDF运行 **16组完整SoC MAXIMUM SDF + 1组无SDF门级功能对照**，全部通过。

**16组SDF的初始化、正常工作、最终复位阶段均为0条动态时序违规。** 时序消息与notifier全程开启，没有窗口屏蔽或修改SDF。仍有17条负IOPATH截零和每组5条时间0的PAD模型消息，不能称为完整或无损签核。

## 1．先读哪些证据

| 文件 | 作用 |
| --- | --- |
| [analysis.json](analysis.json) | 来源、全部门禁、半周期路径与PAD消息明细 |
| [audit.json](audit.json) | 原始回标分类与16组动态事件统计 |
| [results.json](results.json) | 17组功能结果、计数、实际复位相位 |
| [input_manifest.json](input_manifest.json) | 原网表/SDF、库模型、固件与实际仿真输入SHA |
| [SDF首组日志](sdf_max.log)、[无SDF对照](gate_zero.log) | 核对实际PAD延时、CPU数值自检、DMA重叠与复位 |
| [SRAM输入Setup](sram_timing/sram_input_setup.log)、[Hold](sram_timing/sram_input_hold.log) | 输入寄存器到宏的下降沿检查 |
| [SRAM输出Setup](sram_timing/sram_output_setup.log)、[Hold](sram_timing/sram_output_hold.log) | 宏下降沿到AXI/CPU接收上升沿的检查 |
| [时钟报告](sram_timing/clocks.log) | sys_clk20ns，0/10ns边沿且Propagated=y |
| [补充证据](supplemental_evidence.json) | 17条负IOPATH原对象/原SDF片段、四项阶段退出码与STA后输入SHA复核 |
| [review.tar.gz](review.tar.gz)、[清单](review_manifest.json) | 全74份小型原始日志/命令/报告的逐文件可核验归档 |

完整本机目录为lab4/postsim_sram_reset_5191064_20261027；大网表/SDF、库模型、simv与编译数据库保留在对应服务器目录，不进Git。

## 2．与现有main比较

| 项目 | main1192c32（物理e15483c） | 修正版5191064 |
| --- | --- | --- |
| 整颗含PAD面积 | 3.7956390976mm² | 3.7956390976mm² |
| 全局Setup/Hold | +0.226/+0.019ns | +0.371/+0.019ns |
| SDF功能组数 | 16/16通过 | 16/16通过 |
| 回标error/缺失实例/缺失检查 | 0/0/0 | 0/0/0 |
| 初始时序消息 | 每组9条，共144条 | 16组共0条 |
| 正常工作时序消息 | 0 | 0 |
| 最终复位时序消息 | 每组1条，共16条 | 16组共0条 |
| 最终复位相位 | 固定2ns | 首组2ns，其余0.25至19.85ns |
| 负IOPATH截零 | 19条 | 17条，限制仍存在 |
| PAD BUS CONFLICT消息 | 每组时间0有5条 | 每组时间0有5条；时间0以后0条 |
| NPU批次计数/实际重叠 | 1035 / 任一93、读62、写93 | 1035 / 任一93、读62、写93 |
| 测试台观测CPU等待拍数 | 3658 | SDF3660，无SDF3659 |

面积没有增加，Setup全局余量提高0.145ns。初始9条事件在本次实现中也未再出现，但不能把所有改善都归因为一个接口改动：RTL、综合与实际布局布线都变了。旧报告保留，未将其原始10条复位消息改成零。

观察拍数不等于CPU或纯NPU性能：本次完成标志从SRAM宏真实写入处观察，原版使用AXI侧请求；实际写入相位和PAD/SDF延时也影响循环何时看到标志。不能由3658到3660宣称硬件慢2拍。NPU内部1035和DMA/MAC重叠计数保持一致。

## 3．半周期是否真实检查

补充STA只读加载同一个step34数据库；不做ECO、不保存设计、没有修改冻结work输入。以48个SRAM输入引脚和32个输出引脚为范围，每种检查列出20条最差路径。

| 路径 | 真实边沿关系 | 最差Setup | 最差Hold |
| --- | --- | --- | --- |
| 命令寄存器→SRAM | 系统上升沿0ns→下降沿10ns | +6.290ns | +10.194ns |
| SRAM→AXI/CPU接收寄存器 | 系统下降沿10ns→下一上升沿20ns | +3.188ns | +11.476ns |

输入最差Setup为port_wdata_q_reg[0]到宏D[0]：Required8.374ns、Arrival2.084ns，差6.290ns。输出最差Setup为宏Q[15]到CPU操作数寄存器：Required21.263ns、Arrival18.075ns，差3.188ns。到达/要求值含实际时钟树延迟与0.470ns setup uncertainty，不能直接当成路径周期。

输出报告明确写“triggered by trailing edge”，接收为“leading edge”；时钟报告sys_clk传播、0/10ns边沿。没有把反相SRAM时钟声明为与系统无关，也没有新加false path或放宽20ns。

## 4．这次究竟验证了什么

每组都通过Debug SBA真实AXI路径写入完整2048字镜像，检查无镜像、错密钥、部分/乱序/字节装载不能让CPU抢跑；提交后检查复位释放余量。CPU逐值验证隐藏层、六个INT32分数和类别，并核对64个tile及两级MAC次数。12组训练双样本覆盖24条训练输入，4组随机双样本覆盖8条随机输入。

实际DMA读/MAC重叠62拍、写/MAC重叠93拍；不是把DMA busy当作计算并行。第一层64、第二层6个INT8乘法器，INT32累加、8KiB主SRAM、两个64B缓存和批内tile复用保留。

ACTIVE_START=600ns至ACTIVE_END=238840ns包含装载、保护、自检和统计。初始与最终复位窗口也检查且保留消息。复位偏移2ns和其余15个相位均实际运行，复位后验证boot许可撤销及宏CEN禁止。有限相位/输入测试不等于覆盖任意模拟初态。

## 5．保留的模型与工具限制

回标主汇总warning为3609；后续还有17条SDFCOM_NIOD，分类总标记3626。SWC2520、IWSBA1088表示对应连接仍回标；UHICD1是顶层输出互连的DEVICE处理；NIOD17表示部分负IOPATH被VCS截0。已使用negdelay、neg_tchk、NTC及RECREM，原SDF未手改；原对象与数值片段保留在supplemental_evidence.json。数量19降17不代表已经支持负IOPATH。

所有17次运行仍各有5条时间0的PAD“BUS CONFLICT”显示。原生IO模型在PAD为X且countdrivers非零时打印该消息；本次与历史main同样存在，时间0以后没有该消息。没有使用bus_conflict_off。它不属于setup/hold回标错误，也不能被说成已证明PAD上电或ESD安全，原日志完整保留。

## 6．来源与复现

物理上传为20261026_214621_5191064；后仿上传为20261027_003144_postsim_bfc53d4，bfc53d4仅补充功能证据与文档，RTL和后仿脚本与5191064一致。STA补充脚本见eda/server/postsim/sram_timing.tcl。所有原始仿真输入在STA之后再次SHA复核一致，当前没有活动EDA/VCS进程。

按eda/README.md重新打包并新上传，执行check_env、run_eda、collect三个独立阶段；完成后按eda/docs/后仿真操作指南.md执行postsim.py run/status、timing、fetch。每次新目录，不改旧work，不拼检查点。

这是单TT、1.8V、25°C、MAXIMUM SDF和有限输入/相位的验证。所列RTL、物理流程和动态检查通过，但未执行独立晶圆厂DRC/LVS、多PVT、IR/EM/ESD、形式等价或活动功耗重估。
