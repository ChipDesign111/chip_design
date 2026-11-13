# 统一系统复位与Wire Bond最终结果（2026-11-13）

本轮以新RTL dea5584重新综合、完成34步物理实现，再进行同源TT后仿、同数据库补充STA及最终Lab5。前版be4a7fc的两条真实复位事件在本轮原生产激励下均未重现；Wire Bond从原始9处降为0处。

| 项目 | 新版实测结果 |
| --- | --- |
| 物理源码 | dea55844d707a146668a8d91b619ae109ca1dc6d，34步同源，环境/EDA/整理/入口退出码全部0 |
| 综合 | 68,703单元；cell面积2064513.940 µm²，含SRAM 401443.591 µm² |
| Die（含PAD） | 3.7956390976 mm²；系统20 ns |
| 原生Density | 75.129%，Innovus原始日志第29024行；不等于Filler占满率 |
| TT静态时序 | Setup +3.825 ns；Hold +0.115 ns |
| TT后仿 | 16组SDF及1组独立功能对照，17/17功能通过；绑定错误/缺失/全部阶段动态违规/负IOPATH截零均0 |
| SRAM半周期输入（多角最差报告） | Setup +1.951 ns；Hold +9.935 ns |
| SRAM半周期输出（多角最差报告） | Setup +0.367 ns；Hold +10.879 ns |
| TT共享复位到请求D | Setup +6.714 ns；Hold +11.064 ns |
| 最终DRC | 523项；原始2426层次/14515展开；课程DRM/ESD/MOM/LUP四类之外0 |
| LVS | CORRECT，完整605项属性；没有SRAM Box或虚连捷径 |
| ERC | 7层次/977展开；原生IO/外环课程残项逐对象核对；ERC Clean=False |
| 最终天线 | 62项，0违规 |
| 最终Wire Bond | 64项，0违规；原始WB规则保留 |

## 修复与回归

旧版上游AXI先复位、SRAM接收侧仍等待独立延迟，分别使请求D的Setup和地址D的Hold违规。相同SDF/模型/固件/激励的被动波形证实了该因果关系，不能用普通同步短路径优化解释或豁免。

按用户授权，POR和NDM请求分别经过两级下降沿采样；POR及功能复位发生器的释放也对齐下降沿。CPU、AXI、NPU、SRAM桥和主存使用同一功能复位边界，取消仅接收侧额外延迟。根请求最多两个下降沿识别，后续保留原两组各四级发生器；时钟必须运行。JTAG TAP仍用独立外部复位。已接受的SRAM载荷不异步撕裂，在下一下降沿完成一次，共同复位后停止新请求。没有RTL固定延时、时钟门控、SDF改写、新增假路径或关闭检查。

部署前功能证据单列在[功能验证](../../../report/functional_validation.json)：44组数据回归、80个POR和80个NDM相位、两种模型各320场景/642次接受与实际写一致，以及开启原生宏时序检查的16个完整SoC复位相位。本次生产TT后仿保留原始上电、16个最终复位相位及NTC/RECREM/notifier/IO冲突检查。

WB修复保留步骤10对34个固定Bond PAD的M5/M6原生信号布线避让，spacing=2.5 µm，共68个分层对象。PG只不受信号障碍影响，最终WB仍检查全部金属。实际映射自动ICG、受控FF及被排除TT组合实例均0，完整CPU、70个INT8乘法器、8KiB主存及双tile保留。

同库STA已核实sys_clk为20 ns、0/10 ns且传播，复位路径从真实末级i_rstgen_main同步器Q到port_req_q/D，12份补充报告均有真实路径及非负余量；SRAM汇总为多角排序前20路径的最差值（Setup来自SS、Hold来自FF−40），不是TT专属数值；仅只读报告，不ECO、不保存。四角内部物理检查保留，但本轮只执行TT SDF，不声称快慢角新后仿通过。

最终含Seal Ring外框1979 µm，面积3.916441 mm²，与含PAD原Die单列。课程允许的DRC和逐几何ERC残项不删改原始计数，未知/核心残项不豁免；不称ERC Clean或完整代工厂签核。

## 来源与交付

- [实测数据](summary.json)
- [917项物理与后仿/Lab5报告SHA和回传凭据](report_provenance.json)
- [TT后仿审计](tt_postsim_audit.json)
- [补充STA](supplemental_sta.json)
- [前版对比及相同激励SHA](comparison.json)
- [ERC逐对象核对](erc_review.json)

物理：`/home/s2400011041/Desktop/fullstack_chipdesign/uploads/20261113_112238_dea5584`。
TT：`20261113_124759_postsim_vcs_tt_dea5584`。
Lab5：`/home/s2400011041/Desktop/fullstack_chipdesign/uploads/20261113_205904_lab5_22a168c`，流程脚本源码22a168c9c3c5e579f51d101f45e803b8f0ba2844；与物理源码分别记录。
本地核验包：`lab5/system_reset_unified_20261113`，物理917项、后仿84项、Lab5 61项。
最终GDS SHA：`8187f27d46be91c92842b610a3df502b8bcf16a3162502559e09f7cf1f74d400`；DRC/LVS/ERC/天线/WB均绑定同一最终GDS。

本轮只提交推送xzx，没有改动main。只读观察main=266bca3ac99998df5375c61301a9102a6f6fc461，其独立RTL更新不由本轮结果验证。大GDS/DEF/SDF/SPEF/DB及授权模型留服务器。未执行Dummy后重新提取/STA、完整RCminmax/SI/IR/EM或正式foundry签核。复位相位回归和STA不等于穷尽所有异步亚稳态行为。

与be4a7fc相比：TT真实动态事件2→0，Setup/Hold +3.765/+0.091→+3.825/+0.115 ns；综合单元增加27、cell面积增加439.040 µm²（约0.02127%），Die不变，WB保持0。没有相同活动功耗测量，不宣称功耗改善。

## 服务器GUI查看

在服务器终端执行：

```bash
cd /home/s2400011041/Desktop/fullstack_chipdesign/uploads/20261113_205904_lab5_22a168c/soc-stu/layout/workspace
source /etc/profile.d/eda.sh
virtuoso &
```

选择库`my_soc_top_final`、单元`my_soc_top_postDummy`、视图`layout`。该workspace下保留DRC/LVS/ERC/天线/WB原始报告和数据库。项目根`README.html`链接最新物理、TT与Lab5；原生实现利用率见本地核验包`implementation/core/evidence/innovus_01_to_34.log:29024`，不是人工生成摘要。
