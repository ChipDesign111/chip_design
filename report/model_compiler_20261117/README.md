# PyTorch混合执行编译器验收：2026-11-17

基线为单/双层FC分支eea7561。此次未修改RTL；新增PyTorch FX前端、自动INT8量化与范围检查、CPU/NPU分配、分块与内存规划、RV32IM代码生成，以及完整SoC装载和逐层验证。

8组完整SoC运行均通过。机器码实际运行在CV32E40P上，NPU任务使用真实AXI DMA。通过Debug SBA读回输入及各层张量并逐字比较整数参考；[部署示例](example_package/manifest.json)和[实际输出](example_package/actual_output.json)均已保留。参考值不嵌入生成的CPU程序。[源码、输入权重与证据SHA](summary.json)。

| 用例 | 实际NPU任务数 | 完整SoC观测周期 |
| --- | ---: | ---: |
| 混合网络，输入1 | 2 | 3724 |
| 同一机器码，另一输入 | 2 | 3724 |
| 相同网络强制全CPU | 0 | 7602 |
| 65→9、batch=2，K分块，Tanh在CPU | 2 | 2044 |
| Linear累加超过INT22时自动CPU回退 | 0 | 496 |
| 9→41，N分块 | 2 | 1959 |
| CPU标量/张量减法、乘法和Softmax，batch=2 | 0 | 2961 |
| 保留HAR训练权重，NPU→CPU ReLU→NPU | 2 | 4019 |

混合及全CPU两种分配的整数结果相同；示例混合执行减少51.0%周期，该结果不代表所有网络。训练HAR本次为单样本、通用量化及CPU层间处理，不能与旧专用四样本2700拍程序作同任务性能对照，也没有声称通用编译结果满足旧专用路径的周期预算。

每个用例的PyTorch浮点误差单列于summary.json。混合示例两种输入最大绝对误差分别0.001304和0.000563；HAR单个运行样本为0.073597。RTL与整数参考完全一致，不等于与浮点模型完全一致，更不等于完整数据集分类准确率验证。

已验证不支持的CPU算子、容量超限、非有限输入均明确拒绝。CPU回退目前覆盖Linear、ReLU、Sigmoid、Tanh、Softmax、Add/Sub/Mul和有限形状操作，尚不包含任意PyTorch算子。首次模型部署须提供源码/工厂、权重、输入形状及代表性校准数据。使用方法见[编译器说明](../../model/compiler/README.md)。

本地依赖为PyTorch 2.15.0+cpu、Python 3.12。仓库及硬件外围检查通过。没有重新综合、PNR、STA、SDF或板测；CI新增主机编译检查，完整SoC证据来自本地ModelSim。
