# main 266bca3与xzx新增流程整合

以main 266bca3的16-MAC共享INT8阵列、INT22累加/偏置、128B取指缓存、CUT_SLV_AX、DMA和reuse8固件为核心。六个核心源码文件与main逐文件SHA一致，见integration.json。

接入xzx已测的公共系统时钟域复位边界，保留main其余SoC连接；JTAG独立外部复位保留。新增原生Bond PAD信号避让、jump-first天线、原生非负TT表单元选择和普通DFF使能实现、完整Lab5/逐对象ERC核对、同源SHA回传及一键串行流程。原生库、SDF和检查不修改。

当前合并后41组计算/8组DMA/完整SoC/80 POR与80 NDM相位通过，完整SoC2700拍、硬件2695拍。包含24个已有量化模型测试样本（六个四样本批次）及随机/定向样本，不将其表述为硬件训练。

新综合、34步、TT SDF、同DB STA及Lab5待执行；不能将main旧密度72.509%、Setup/Hold +0.335/+0.050 ns或xzx旧结果当作本轮结果。保持20ns和含PAD Die≤3.8mm²，采用main单TT配置；.1/.05ns沿用main优化参数，正常零违规和原生电气/物理规则仍单列核验。TT负路径、复位事件全部保留审计，不用工作窗口PASS代替全程。

独立无SDF对照沿用main的unit-delay模式，适配取指缓存的仿真调度；所有SDF用例保持NTC/RECREM/notifier与原生模型检查。16个SDF用例覆盖六个四样本批次与十个随机种子，保留全周期最终复位相位覆盖。
