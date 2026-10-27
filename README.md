# INT8 HAR完整SoC

2026-10-27，xzx已完成正常条件下的四库角EDA及TT/快角/慢角三组SDF验证：系统20ns，含PAD整颗 **3.7956390976mm²**，四角最差Setup/Hold **+0.001/+0.020ns**，三组各17例通过，全部SDF阶段动态时序违规0。实测逻辑密度74.138%，规划/优化预算85%。详见[本轮结果与main比较](eda/results/native_mux_dff_20261027/README.md)。

main保持`d40b217`，当前xzx功能RTL与main完全相同；本轮修改综合/后端的寄存器映射及运行脚本，后续改动没有自动合并main。原main的TT验证保留为[历史基线](eda/results/sram_reset_20261027/README.md)。TT/快角仍有18/438条负IOPATH截零消息，慢角0条，原始警告如实保留，不宣称完整延时无损或独立工艺签核。

设计包含CV32E40P、AXI、JTAG Debug、8KiB主SRAM和64→32→6 NPU。第一层每拍2输入×32输出，第二层1×6，共70个INT8乘法器；偏置、累加与分数为INT32。DMA从主SRAM向两个64B权重tile搬运；当前tile完成本批所有样本的相关计算后替换，读写可与MAC并行。CPU在完整镜像覆盖和正确密钥提交前禁止启动。

从本机打包、上传开始，按[EDA操作指南](eda/README.md)运行独立的环境检查、EDA、结果整理三个脚本；物理完成后按[后仿指南](eda/docs/后仿真操作指南.md)执行并回传。每次上传新建目录，原包、解压文件和全部结果仅在该版本目录展开。服务器GUI从版本README.html查看。

| 目录 | 内容 |
| --- | --- |
| [rtl](rtl/README.md) | 当前完整SoC及filelist |
| [eda](eda/README.md) | 正式部署、服务器脚本、步骤说明和正常结果 |
| [model](model/README.md) | 训练模型、量化参数和整数参考 |
| [test](test/README.md) | INT8、DMA与启动保护功能回归 |
| [report](report/README.md) | 架构、寄存器及验证范围 |
| [fpga](fpga/README.md) | FPGA工程；本轮验收在ASIC服务器 |
| [tools](tools/README.md) | 正常工程入口、权重导出与依赖 |

```bash
python tools/project.py doctor
python test/int8/run.py --count 32 --trained --soc
python eda/remote.py run
```

本机功能测试使用Icarus，完整SoC另需ModelSim。EDA总控使用Python和OpenSSH。大GDS/DEF/SDF/SPEF、授权库及数据库保留服务器；核心结果回传本地lab4独立新目录。开发自检/临时工具与退役RTL仅保存在本地archives，不进入分支。第三方固定输入及许可见[组件声明](report/THIRD_PARTY_NOTICES.md)。
