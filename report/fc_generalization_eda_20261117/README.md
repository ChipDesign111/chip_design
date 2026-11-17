# 单/双层FC、模型编译与完整EDA验收

已完成全部必需阶段，按既有课程例外范围通过。物理实现与TT后仿源码为ee203a3；最终M6填充配置为febec45，Lab5在同一份冻结物理输入上重新执行并通过。[最终汇总及输入SHA](final_result.json)。原始失败日志及pipeline.json保留，没有改写成成功。

## 验收结论

| 项目 | 实测 |
| --- | --- |
| 原始四样本完整SoC | 2700→2700拍，硬件2695→2695拍，增幅0%，满足≤5% |
| 匹配的NPU计算用例 | 41/41周期与两层ISSUE计数保持不变 |
| 计算与存储规模 | 共享16个INT8 MAC、INT22累加、双64B权重bank、一个8KiB主SRAM |
| Genus Cell Area（含SRAM宏） | 2.252109mm²，较287ae40的2.067330mm²增加8.938% |
| 主SRAM宏本体 | 0.401444mm²，容量与宏类型不变 |
| 原生逻辑Density | 82.746%，基线74.633%，增加8.113个百分点 |
| 含PAD实现外框 | 1948.24×1948.24µm，3.795639mm² |
| Lab5 SealRing外包络 | 1979×1979µm，3.916441mm² |
| 20ns TT最终Setup/Hold | +0.100/+0.001ns，TNS与违例路径均0，电气DRV均0 |
| 实现输入与结果核验 | 34步同源，635项回传文件SHA通过 |
| 门级验证 | 19/19功能通过：18组TT SDF、1组独立功能对照 |
| SDF完整性与动态检查 | 回标错误/缺失实例/缺失检查/负IOPATH截零均0；所有阶段动态违规0 |
| 最终Lab5 | M2.S.2=0、M6.R.1=0、非课程排除DRC=0、LVS正确、已审阅ERC、天线0、WB64项全0 |

3.8mm²门槛按既有流程检查“含PAD实现外框”；若按SealRing外包络计算，本版是3.916441mm²，超过3.8mm²。两者不能混用，也不能把Cell Area代替Die面积。Hold只有1ps余量，结论只覆盖当前single-TT、SI关闭、原生低RC配置；尚未新增全PVT/SI、功耗、IR/EM、填充后RC重抽取或板测。

## 面积为什么增加

[同口径模块比较](final_synthesis_comparison.json)保留原生area.rpt来源及SHA。287ae40与任务起点main f2b9814的RTL相同；物理配置维持20ns、1648µm核心、150µm边距及85%优化密度。基线与最终版的自动门控映射不同，因此总增幅包含通用化和复位时序修复成本。

| 层次（包含关系，不重复求和） | 基线mm² | 最终mm² | 增幅 |
| --- | ---: | ---: | ---: |
| i_cpu | 0.383892 | 0.403706 | +5.161% |
| i_dma | 0.037639 | 0.040565 | +7.774% |
| i_mainmem | 0.403542 | 0.404168 | +0.155% |
| i_npu_subsystem | 0.797545 | 0.921791 | +15.579% |
| i_npu_subsystem/i_npu_core/core | 0.490759 | 0.550159 | +12.104% |
| i_npu_subsystem/i_npu_core/weights | 0.068385 | 0.068255 | -0.189% |

保留自动门控的首轮通用版为2.124285mm²，比基线多0.056954mm²；全局取消自动插入门控后为2.252109mm²，再多0.127824mm²。这个差值包含映射与工具重优化影响，不能把全部8.938%归为通用计算阵列成本。数组声明容量与MAC数保持不变，但原生带使能FF和门控结构变化仍会改变面积。

simple_npu_top扣除core及weights后的自身面积由0.237556增至0.302569mm²。首轮增量主要落在结果读回和动态控制组合逻辑；最终版还包含取消自动门控带来的FF映射成本。编译器与CPU定点软件内核没有作为新增RTL综合，机器码、权重和LUT共同占用现有8KiB。

[原生日志密度与SHA](final_native_density.json)：非固定标准单元Placement Density为1788504/2161451µm²；若只按85%全局预算，余量约48729µm²（0.0487mm²）。这只是面积规划估计，不保证另一算子的局部摆放、布线、供电和时序可闭合；先前0.1647mm²估计属于未通过最终验收的首轮。Filler后的100%不能当作逻辑Density。

原四样本任务有8960次MAC。保持当前调度时，8 MAC的乐观完整SoC下界约3018拍，高于允许的2835拍，因此保留16 MAC。[计算依据](array_tradeoff_bound.json)。12 MAC尚未实测，不能承诺满足5%。后续压面积应测量读回逻辑和复位安全门控方案的收益。

## 修复过程与保留的失败

1. aca6c09：实现与TT通过，Lab5发现3项M2.S.2。信号VIA2顶边与电源PAD宽M2间距只有0.45µm，规则要求0.6µm；在28个PV*电源IO上加入METAL2信号避让0.65µm，PG豁免。[诊断](io_m2_diagnosis.json)、[原始失败](lab5_failure.json)。
2. d03513b：M2修复通过真实Lab5；TT在初始复位发现3个NPU自动ICG使能违规。[事件记录](reset_gating_failure.json)、[独立Lab5](io_m2_lab5_pass.json)。
3. 91b0a74：取消NPU核心自动门控后，NPU事件消失，但CPU出现10个同类初始事件，说明局部修复不足。[记录](core_only_gating_failure.json)。
4. ee203a3：全局关闭自动插入门控，保留RTL寄存器使能与library_enable；原生映射和布线网表均确认ICG为0，所有SDF阶段动态事件清零。[映射核验](final_gating_mapping.json)。最后Lab5剩M6覆盖29.6431%低于30%。[密度失败](m6_density_failure.json)。
5. febec45：仅将普通M6大Dummy生成间距1.5→1.2µm，增加实际填充。原始30%检查及DRC规则SHA不变。新上传重新执行完整Lab5，所有必需检查通过，并绑定ee203a3的同一物理GDS/CDL。

最后一步只改Lab5填充参数，RTL、编译器、综合/PNR源与TT输入未变；因此续跑Lab5，没有重复综合或把其他版结果拼接到新物理版。原failed pipeline.json保留，最终汇总记录这次有来源的接续。

## 时序与模型覆盖

[最差路径及报告SHA](final_critical_paths.json)：Setup从共同复位同步器Q至NPU的douta_reg[13]/D，Hold位于JTAG CDC请求链；最终最差路径均不是MAC乘法器。软Hold目标0.05ns不是验收阈值，本轮按既定WNS≥0、TNS=0、违例路径0验收。

[同DB、无ECO的SRAM半周期STA](final_sram_timing.json)：输入Setup/Hold +6.181/+10.227ns；输出+2.546/+11.593ns；共同复位至请求寄存器D +5.591/+11.436ns，全部为正。

新增CPU/NPU混合模型逐字检查31项，65→41跨K/N分块模型检查42项，均通过真实SBA读回；SDF观测分别3725/4243拍。原始四样本SDF观测2701拍、NPU952拍，与同一后仿框架首轮相同；不同RTL/门级testbench观测窗口相差一拍，不与RTL2700直接混为一条回归。

[FC接口与65→41分块讲解](../fc_modes.md)、[PyTorch编译部署](../../compiler/README.md)及[8组完整SoC编译验收](../model_compiler_20261117/README.md)区分了整数正确性、量化误差与模型准确率。当前CPU回退只覆盖已注册内核，未注册算子及总8KiB超限会拒绝；不声称任意PyTorch图都可部署。

## Lab5课程例外与交付

最终原始DRC仍保留课程规定的ESD/LUP、MOM.R.2和DRM.R.1残项；ERC为7个层次/977个展开残项，经原生PAD及外部衬底几何审阅接受，erc_clean=false。具体计数在[最终汇总](final_result.json)，不称foundry waiver或ERC Clean。既有Lab5还在私有PVDD2CDG/PVDD2POC拷贝中各添加一个PP矩形处理CO.R.4；共享PDK和冻结物理输入未改变，几何变更单列保留。

物理/TT输出位于工作区lab5/fc_generalization_no_auto_gating_20261117；最终Lab5输出位于lab5/fc_generalization_m6_fill_20261117。服务器三个upload及各包SHA、最终GDS/CDL SHA见final_result.json；最终GDS SHA=e16007dff3a12f9391e64e8d7c1baab102e7fe3c1ca9173a8e87d23480d19c85。

[清理清单](cleanup.json)记录42项、322582569B缓存及一次性文件；[后续清理](cleanup_followup.json)另记录一个语法检查缓存和两份服务器probe Tcl拷贝。正式工具、模型与数据、编译依赖、原始失败/成功日志及其他用户工作树保留。[接续入口](handoff.md)。
