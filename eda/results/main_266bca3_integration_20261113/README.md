# main 266bca3核心整合后的完整流程结果

主线16-MAC/INT22核心与xzx公共复位、TT单元选择、Wire Bond和Lab5流程已整合。本表只使用新源码287ae40129c4e7873dcca2e6281bb1a2f4a414d6的新综合、34步、TT SDF、同数据库STA及Lab5结果。

## RTL与回归

16个共享INT8 MAC、INT22偏置/累加、两组64B权重tile、8KiB主SRAM、128B取指缓存、CUT_SLV_AX及main的DMA/reuse8固件保留。NPU/core、weight store、DMA、ifetch和bootram六个关键文件与main 266bca3逐字节SHA一致。SoC只移植用户已批准的共同系统复位边界，根请求最多两下降沿识别，时钟须持续；保留独立JTAG TAP外部复位。已接受SRAM载荷完成一次，共同复位后停止新请求。

41组计算、8组DMA响应、完整SoC和80 POR/80 NDM相位通过，SoC2700拍/硬件2695拍；含24个已有量化模型测试样本，未在硬件训练。部署前完整回归的116个源码SHA再次逐项匹配，未重复声称旧RTL结果验证新源码。

## 综合与实现

| 指标 | main已有基线 | 本次同源实测 |
| --- | ---: | ---: |
| Cell面积（含SRAM） | 2,023,900.544 µm² | 2,067,330.381 µm² |
| 映射实例 | 66,348 | 64,979 |
| 含PAD PNR Die | 3.7956390976 mm² | 3.7956390976 mm² |
| 原生Density | 72.509% | 74.633% |
| TT Setup/Hold | +0.335/+0.050 ns | +0.350/+0.050 ns |

20ns、core1648µm及150µm边距、85%优化预算保留。恢复main原生使能/自动门控和medium综合努力等级；实测自动门控443、受控FF 3282，不以禁止所有这类单元代替验证。114种原生TT负表组合主单元避用，实际残留0；原模型、时序值和SDC不改。

Density直接引自Innovus原始日志第29650行，没有手算替代原结果；与含Filler占满率区分。首轮fddabe5沿用旧mux-DFF/no-ICG/high策略导致综合面积2.269122mm²，独立通过23步后主动停用，未声称完成；dec9319配置标识错误在EDA前停止，均有原始SHA证据。当前记录不拼接这些候选检查点。

## 静态时序和TT后仿

34步输入身份一致，环境/EDA/整理/入口均0；最终Setup/Hold TNS和违规路径0，电气/default DRC、布局、信号、核心PG和天线正常复核。IO库抽象项保留同源原生几何依据。单TT/25°C，原生低RC、SI off，不称完整RCminmax。

同一最终DB只读补充STA：SRAM输入Setup/Hold +6.307/+10.045 ns；输出+2.783/+11.592 ns；共享复位至port_req_q/D为+5.616/+11.703 ns。报告有真实下降沿/上升沿传播时钟及路径，不ECO、不保存。

VCS16组SDF加1组独立unit-delay功能对照，17/17功能通过；绑定错误/缺失和全部阶段动态违规0，负IOPATH截零0。所有SDF用例保留NTC/RECREM、负检查、notifier和原生IO冲突检查；独立无SDF对照的检查关闭不作为动态时序证据。六个四样本批次与十个随机种子，最终复位覆盖完整20ns周期。

上电板级驱动在2ns接通，时钟前40ns低/50ns首上升沿，此后20ns周期；与main旧首升10ns激励不同。旧main每例28个初始复位事件和21条负路径截零如实保留，不能把消息变化单独归因于RTL，也不能只用工作窗口PASS替代全程检查。

## Lab5与边界

同一最终GDS/CDL：WB 64项、0违规；天线62项、0违规；LVS CORRECT，完整605项属性，无SRAM Box/虚连捷径。WB保留34个Bond PAD在M5/M6的原生信号避让（spacing2.5µm、68分层对象），所有金属仍参与原WB规则检查。

DRC原始2426层次/14515展开，课程DRM/ESD/MOM/LUP之外0；ERC原始7层次/977展开，逐几何核对原生IO/外环课程残项，ERC Clean=False。没有删改原始规则/计数；未知或核心残项不豁免，不称完整foundry签核。

含后加Seal Ring外框1979µm，面积3.916441mm²，与含PAD的PNR Die单列。未执行Dummy后重新提取/STA、完整RCminmax/SI/IR/EM或形式等价；有限复位相位测试不是亚稳态MTBF证明。没有相同活动功耗分析，不宣称功耗改善。

## 来源与查看

- [核心SHA、合并选择与回归](integration.json)
- [完整实测数据](summary.json)
- [原始报告SHA/回传凭据](report_provenance.json)
- [TT审计](tt_postsim_audit.json)
- [同DB路径](supplemental_sta.json)
- [与main已有结果比较](comparison.json)
- [已定位SDF工具警告](tt_warning_review.json)
- [完整部署来源](deployment.json)
- [退役候选证据SHA](retired_candidates.json)
- [仅保留最新服务器版本及容量](storage_policy.json)
- [ERC逐对象核对](erc_review.json)

物理：`/home/s2400011041/Desktop/fullstack_chipdesign/uploads/20261113_220745_287ae40`；Lab5：`/home/s2400011041/Desktop/fullstack_chipdesign/uploads/20261113_225800_lab5_287ae40`。
本地完整核验包：`lab5/main_266bca3_final_20261113`。大GDS/DEF/SDF/SPEF/DB和授权模型留服务器。
在最新Lab5的`soc-stu/layout/workspace`执行`source /etc/profile.d/eda.sh`及`virtuoso &`，打开库`my_soc_top_final`、单元`my_soc_top_postDummy`、视图`layout`。项目根README.html链接最新三个关联目录。

本轮用户已授权与main合并；结果仅绑定上述整合源码，不验证后续独立main改动。

3591条SWC和1164条IWSBA原文均说明延时仍回标；1条UHICD位于i_pad_tdo/PAD到上层accOutput，原文为上层INTERCONNECT忽略、PAD DEVICE延时应用。保留原警告，不声称外部板级/JTAG线路完整时序验证或100%端口/互连覆盖。回标零缺失指标限于报告的实例和时序检查。

原生Density对应服务器work/evidence/innovus_01_to_34.log第29650行；本地补充tt_sta_expanded/native_innovus.log.gz解压后SHA与原日志一致。两个TT展开路径也逐项SHA核验，原675项清单保持不动。
