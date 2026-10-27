# 当前设计说明

当前xzx已完成四个匹配库角的完整34步EDA，以及TT、FF−40、SS125三种SDF后仿，每种17例通过。系统20ns，含PAD整颗3.7956390976mm²，最终最差Setup/Hold+0.001/+0.020ns，全阶段动态违规0；[完整结果与main对比](../eda/results/native_mux_dff_20261027/README.md)列出来源、警告和未执行项目。

main保持d40b217。两分支功能RTL相同，本轮解决的是综合映射：使用普通DFF加数据选择器实现使能，避免自动门控和库内E/SE控制在复位边界产生独立时序违规。[质量跟进](quality_followup.md)说明因果和实测结果；[SRAM接口修正](reset_fix.md)说明已合并main的RTL改动。功能正确和物理时序通过分别有证据，不能互相替代。

从[架构](architecture.md)理解数据通路，再看[NPU](npu.md)、[MMIO](mmio.md)、[DMA](dma.md)、[SRAM/启动](sram.md)。[开发与验证](development.md)介绍功能回归；从打包部署开始见[EDA操作指南](../eda/README.md)。

已有RTL回归覆盖32组随机批次、12组训练双样本共24条输入、DMA错误、重新运行、复位中断及完整CPU自检；原生和便携SRAM各80个复位相位。当前门级后仿通过CPU数值自检、完整启动装载及复位后禁止访问检查，NPU1035拍，DMA读/MAC重叠62拍、写/MAC重叠93拍。门级CPU启动后观测3660拍包含检查开销，不等于纯NPU延迟。详见[功能证据](functional_validation.json)和最终结果中的三个postsim目录。

TT/快角有18/438条负IOPATH截零消息，保留原生模型、原SDF与全部动态检查。未执行独立工艺DRC/LVS、完整RCmin/max、SI、IR/EM/ESD和形式等价；本次正常教学EDA/SDF通过不扩展为完整晶圆厂签核。
