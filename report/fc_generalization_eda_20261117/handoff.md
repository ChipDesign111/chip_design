# 本轮全流程接续记录

用户要求继续当前任务直到额度限制，纯等待时约每半小时人工查询，并安排6小时后在本聊天继续。已创建单次未来继续任务fc-soc-eda，更新具体时间应通过Codex自动化工具，不手写定时器。

## 已冻结并启动

- 本地工作树：C:/Users/zixiang/OneDrive/Desktop/advanced_chip_study/tmp/main-input-window-fix。
- 分支：feat/pytorch-soc-compiler；本次物理输入源码aca6c09。
- 服务器：SSH别名chipdesign。
- 物理上传：/home/s2400011041/Desktop/fullstack_chipdesign/uploads/20261117_011258_aca6c09。
- 本地总控输出：C:/Users/zixiang/OneDrive/Desktop/advanced_chip_study/lab5/fc_generalization_20261117。
- 本地原总控以python eda/pipeline.py运行，当前聊天工具执行session=7813；服务器run_all.sh由nohup启动，最初PID627166。不要根据旧PID单独判断进程身份，需核对cmdline/cwd。
- 先看本地pipeline.json、服务器logs/launcher.log、run_exit_code.txt和实际工作锁；如果原总控仍在推进，不另开同一重任务。

总控命令是：python eda/pipeline.py run --rtl-regression-result test/int8/runs/20261117_011105/result.json --postsim-firmware-dir eda/dist/checked_models_20261117 --output C:/Users/zixiang/OneDrive/Desktop/advanced_chip_study/lab5/fc_generalization_20261117。

## 当前检查约定

本地基线41组计算、8组DMA、原完整SoC和复位契约通过；原始2700/2695拍。单层完整SoC及错误保护也通过，结果single_20261117_011126。部署总控已核对120个RTL/test输入SHA。运行开始后只整理分析报告，没有改变RTL或冻结服务器程序。

最近一次人工查询在北京时间约01:44：Genus通过，已到Innovus27/34。已下载preliminary_synthesis/area.rpt、synthesis.json和geometry.json并生成synthesis_comparison.json。总cell area2.124284845mm²，较287ae40增加2.755%；NPU核心+0.647%，主要增量在NPU外层组合逻辑。Die已测3.7956390976mm²，最终布线/时序/SDF/Lab5尚未确认。原总控内部仍按既有流程自动查询；人工下一次约02:14。只读本地已输出日志不启动第二个服务器任务。

## 后续阶段

完整入口为更新后的pipeline：Genus、Innovus01–34、TT SDF、同DB SRAM半周期STA、Lab5。

新增后仿：eda/dist/checked_models_20261117下有firmware_model_mixed.hex/.checks.json（31项）和firmware_model_tiled.hex/.checks.json（42项，65→41跨K/N分块）。原17例加2例，应为19例：18组SDF、1组独立功能对照。新用例必须出现MODEL_CHECKS_PASS并通过全部张量、ISSUE和STATUS检查；最后K分块可能只有一个tile，允许该最后任务的DMA/MAC重叠为零，不改变旧用例的重叠要求。

若本地总控中断而服务器已完成物理实现，先按明确upload读取状态、检查已存在postsim/Lab5记录，继续已有任务。确实没有启动后仿时，可使用：

python eda/postsim.py run --eda-upload /home/s2400011041/Desktop/fullstack_chipdesign/uploads/20261117_011258_aca6c09 --simulator vcs --sdf-mode tt --extra-firmware-dir eda/dist/checked_models_20261117

随后status，完成后timing、fetch；normal_postsim_pass为true后才串行执行signoff.py绑定同一物理upload。原总控正常则由它自动完成这些步骤，不手工重复。额外固件由test/int8/build_postsim_models.py生成，需要编译器虚拟环境；复制/启动/分析服务器后仿本身不依赖Torch。

## 分析与验收

- 比较287ae40：总cell area2067330.381µm²、64979实例、宏401443.591µm²、含PAD Die3.7956390976mm²、原生Density74.633%、TT Setup/Hold+0.350/+0.050ns。
- 同源基线各层面积在baseline_hierarchy.json，来源是保留的原生Genus area.rpt，不混用9970d6f等旧版。
- 当前约束：20ns、核心1648µm、边距150µm、最大优化密度0.85、含PAD Die≤3.8mm²；不手改PDK/库表/时序值以制造通过。
- 看新work/evidence/synthesis.json、geometry.json、step_33.json、step_34.json；对比原生area.rpt中的NPU top/core、权重bank、CPU、DMA及组合/FF/buffer。
- 绑定同源输入、真实SDF与动态时序、半周期STA、Lab5同一GDS/CDL。保留课程DRC/ERC原始计数及审阅依据，不宣称完整foundry签核。
- 编译器与CPU软件内核没有新增RTL，程序/LUT占SRAM容量；不要把软件目录体积当作芯片面积。
- 真正失败要保留日志；若改RTL/冻结配置，重新跑所需回归并新建版本，不修改旧work冒充续跑。

## 清理已完成

cleanup.json记录42项、322582569字节的本轮缓存和一次性复现文件清理。正式程序、基线/原始日志、输入清单、虚拟环境、用户其他工作树均保留。


## 02:14接续更新

物理34步完成并核验676项；最终Setup/Hold+0.163/+0.048ns，TNS及违例路径0；原生Density77.379%，含PAD Die3.7956390976mm²。TT后仿20261117_020547_postsim_vcs_tt_aca6c09全部19例通过，新增31/42项数据检查通过，回标错误/缺失/全阶段动态事件/负IOPATH截零均0。同DB半周期STA通过，摘要保存在本报告目录。Lab5已启动20261117_021054_lab5_aca6c09，首次人工查询结果文件尚未形成，日志为空不等于失败，原总控继续等待。下一次纯等待人工查询约02:44；若原总控产生完成/失败事件，应立即处理，不重复启动。

## 07:27 修复接续

首轮总控已退出1，Lab5因3项M2.S.2失败，其他阶段结果保留。不是仍在等待。三条普通信号路由在北侧电源PAD下的M2间距0.45µm，小于规则0.6µm；详见io_m2_diagnosis.json和lab5_failure.json。已新增28个PV*电源IO的METAL2信号keepout（0.65µm，PG豁免），原生Innovus读回验证通过，不改PDK或原始GDS。需提交后在新目录fc_generalization_io_m2_20261117重跑完整Genus→34步→19例TT SDF→同DB STA→Lab5。RTL/test未变，可继续使用120项SHA核验的011105回归。冻结旧work未改写。

修复版已提交d03513b，新物理上传20261117_072804_d03513b，输出C:/Users/zixiang/OneDrive/Desktop/advanced_chip_study/lab5/fc_generalization_io_m2_20261117。本地pipeline session=68437，启动北京时间07:28。人工下一次约07:58查询；总控内部已有自动阶段推进。若继续时先检查本地总控是否存活，避免重复上传。

07:58人工查询：新上传20261117_072804_d03513b已通过Genus，到Innovus27/34，running=true、工具错误false。原本地总控68437仍正常推进；下一次纯等待人工查询约08:28。新增文档和失败摘要精简只在本地，RTL/EDA冻结源未再改变。

08:35接续：d03513b的34步完成。TT上传20261117_081941_postsim_vcs_tt_d03513b全部19例功能正确，但18组SDF每组3条初始复位ICG使能违规，54条合计，normal_postsim_pass=false，pipeline68437已退出1。独立Lab5上传20261117_082948_lab5_d03513b已完成并fetch，lab5_pass=true、M2.S.2=0，说明M2修复真实有效，但不能抵消SDF失败。下一版仅取消i_npu_subsystem/i_npu_core/core的Genus自动门控，原生属性与映射后双重检查，保留其他模块门控及library_enable。RTL/test仍未变；需要提交并新上传完整流程。91732的Lab5总控已退出0，无重任务在跑。

08:37启动第三版91b0a74：物理上传20261117_083659_91b0a74，本地总控session12433，输出lab5/fc_generalization_core_gating_20261117，控制台在同级fc_generalization_core_gating_20261117.console.log。08:39已在原生Genus日志确认EDA_AUTO_CLOCK_GATING_EXCLUDED i_npu_subsystem/i_npu_core/core READBACK=true，配置属性有效，综合继续；下一次纯等待人工查询约09:09。RTL/test未变，复用120项SHA核验的完整SoC回归，后续仍由总控串行19例SDF→STA→Lab5。新版本未验收前，不把d03513b的Lab5通过拼接成新版本全过。

09:10查询：91b0a74已通过综合及映射排除核验，到Innovus27/34。Genus面积2186404.615µm²（较287ae40约+5.76%，较d03513b多62119.770µm²）；397个自动门控保留，受控FF实例8100，NPU core无自动ICG。面积/功耗成本需与取消门控的正确性修复分开说明，不再把原2.75%当作最终增幅。下一次纯等待人工查询约09:40。

09:40：91b0a74的完整实现通过，TT/STA完成并fetch，但初始复位在CPU十个ICG出现180条合计事件，NPU此前三处消失；全部19例功能与工作/最终复位无违规。总控12433退出1，未跑本版Lab5。下一版全局关闭自动ICG、保留library_enable，并移除局部排除开关以简化正式实现。仍需提交、新上传和完整重跑。RTL/test未变，120项源SHA回归仍可复用。全局关闭可能增加面积，必须报告实测值；板级功耗未测。

09:44全局方案ee203a3已冻结并启动：物理上传20261117_094344_ee203a3；总控session63896；新结果lab5/fc_generalization_no_auto_gating_20261117，控制台同级.console.log。只关闭自动插入门控，RTL/test未变；保留原生library_enable、TT非负组合库选择、IO M2及WB keepout。已删除局部门控排除开关，正式映射审计要求全局自动ICG为0。下次纯等待查询约10:14。不要重复启动；前面三版原始证据全部保留，不以其他版Lab5通过替代本版全流程。

10:15查询：ee203a3已通过Genus，mapped automatic ICG=0，library_enable受控FF11319，cell area2252109.146µm²（较旧main基线约+8.94%）。已到Innovus27/34，工具无错误。最终密度/时序/SDF/Lab5尚待完成，不能引用前版密度和0.1647mm²估计余量。下一次纯等待查询约10:45。

10:49：ee203a3的TT后仿20261117_103549_postsim_vcs_tt_ee203a3通过，19例功能、18SDF全阶段动态违规0、回标/缺失/截零0；半周期STA全正；物理635项SHA核验，Setup/Hold+0.100/+0.001ns、密度82.746%。Lab5 20261117_104444_lab5_ee203a3已执行完，剩M6.R.1=1，实测密度0.296431<0.3，其他最终检查通过，总控63896退出1。修复仅Lab5 Dummy大M6间距1.5→1.2µm，保留原规则；需要提交后新Lab5-only上传绑定同一20261117_094344_ee203a3，无需重综合或重后仿。禁止覆盖failed pipeline.json。新最终报告汇总继续执行的证据。
