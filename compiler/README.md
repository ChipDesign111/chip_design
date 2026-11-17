# PyTorch → RV32 CPU / NPU 混合部署

新增任务引擎仍在验收中：`--task-engine`选择顺序任务表、自动输入/bias、六种量化激活及写回；连续支持算子一次启动，CPU处理已有Add/Sub/Mul/Softmax等边界。生成task_plan.json/md，详见 [ABI](TASK_ABI.md) 和 [本轮状态](../report/npu_task_engine_20261117/README.md)。不加此参数仍走下述冻结的旧路径。ReLU6/LeakyReLU现也有CPU整数内核。新路径逐值验证同时观察内部交接和融合后的整数边界，不能把未写SRAM的张量当成已物化结果。

入口是一个PyTorch nn.Module和有代表性的浮点输入。编译器使用FX获取静态计算图，进行对称INT8量化、后端选择、FC分块及8KiB SRAM布局，然后直接生成普通RV32IM机器码。芯片上不运行Python或PyTorch，也不需要新的CPU指令。

## 快速运行

在包含本功能的仓库根目录，使用Python 3.12及ModelSim：

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r compiler/requirements.txt
.venv/Scripts/python -m compiler --model model/generic_mixed/model.py --weights model/generic_mixed/data/weights.pth --input model/generic_mixed/data/input.npy --calibration model/generic_mixed/data/calibration.npy --out test/int8/runs/demo/package --simulate
```

Linux使用`.venv/bin/python`。不加`--simulate`只编译；之后可独立执行`python -m compiler.sim PACKAGE_DIR --vsim PATH_TO_VSIM`。模拟通过真实Debug SBA、AXI、SRAM装载全部2048个字并提交启动密钥，真实CPU运行生成程序。完成后通过SBA读回每个中间张量，与整数参考逐字核对，并输出实际读回的`actual_output.json`。

演示模型是Linear→ReLU→Sigmoid→张量乘法/残差加法→Linear→标量乘加→Softmax。两个Linear走NPU，其余运算由真实CPU执行。

## 接入你的模型

模型源码中提供无参数工厂函数：

```python
import torch
from torch import nn

def build_model():
    return nn.Sequential(nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 6))
```

使用`--model your_model.py --factory build_model --weights weights.pth --input input.npy --calibration calibration.npy --out PACKAGE_DIR`。`--weights`接收纯state_dict，采用weights_only=True加载；具有额外元数据的训练checkpoint应先提取state_dict。也可以在工厂中构建并加载模型。只有权重文件无法恢复任意forward计算图，仍需模型定义。

输入为float32 NumPy数组，形状[B,K]，B=1..4。calibration.npy形状[样本数,B,K]；实际部署示例输入也参与确定范围。校准数据应覆盖预期输入域，不能用少数样本的通过代替分类准确率。程序与量化参数在编译后固定，输入数据可在启动前单独替换。当前程序每次启动完成一次forward后停在halt循环；连续推理应用的循环、传感器输入或中断服务需另行集成。

Python API：`compile_model(model.eval(), example_input, calibration_inputs=...)`返回部署包，`package.write(directory, new_input)`使用同一机器码、权重与量化参数生成另一份启动镜像。新输入形状必须一致。

## 自动后端分配

| 图运算 | 执行位置 |
| --- | --- |
| nn.Linear，量化权重/输入为INT8且全部允许输入的累加范围落入INT22 | NPU单层模式，自动沿K按64、沿N按32分块 |
| nn.Linear，累加范围超出INT22但可证明落入INT32 | CPU软件点积，使用RV32M乘法 |
| ReLU、Sigmoid、Tanh、Softmax(dim=1或-1) | CPU定点/LUT内核 |
| 同形状张量Add/Sub/Mul，以及标量Add/Sub/Mul | CPU定点内核 |
| Identity及不改变二维形状的Flatten/view/reshape/contiguous | CPU复制/重标定路径 |

支持残差连接；张量广播不支持。nn.ReLU(inplace=True)仅在输入节点无其他消费者时转换为独立输出，避免破坏分支语义。普通PyTorch函数/方法的支持项见[前端](frontend.py)。当前不包含Conv、Pooling、BatchNorm、Attention、任意Python控制流、动态形状或任意ATen算子的CPU实现。未注册CPU内核的算子在编译时明确报出节点和类型，绝不宣称已自动回退成功。

`--force-cpu`可将所有Linear也交给CPU，用于验证分配前后整数结果的一致性。每层backend及原因、NPU任务列表和代码PC区间写入manifest.json。

CPU回退不是在没有FPU的处理器上原样执行浮点PyTorch。当前整图边界为对称INT8、零点0；Linear权重逐层对称INT8、偏置INT32，NPU要求更严格的INT22全输入域安全界限。CPU累加和重标定均检查INT32界限，缩放、舍入、饱和规则被冻结在[整数参考与代码生成](compiler.py)中。Sigmoid/Tanh使用256项INT8输出LUT；Softmax使用指数LUT和真实CPU整数归一化。量化近似误差与RTL实现误差分别评估。

## 部署包与内存

- firmware.hex / firmware.bin：8KiB启动镜像，包含机器码、权重、初始输入、数据区；bin为小端。
- firmware.S：可读RV32IM指令清单。
- manifest.json：算子分配、量化scale、分块、地址、代码大小及剩余空间。
- reference.json：本次输入的各层整数参考，供验证使用，不嵌入CPU代码。
- 实际SoC仿真后另有actual_tensors.hex、actual_output.json及soc.log。

代码从SRAM低地址向上增长；各层张量、权重、bias和LUT从高地址向下分配，顶端64B保留为状态/统计邮箱。当前保留所有层的中间结果，尚未做生命周期复用。检查的是代码、权重、数据及保留区的总容量；重叠或超出8192B即拒绝编译，没有把较大模型的容量问题转移给CPU来掩盖。

启动镜像沿用已有全SoC/FPGA装载格式。CPU把当前输入段写入NPU输入寄存器，硬件DMA搬权重；最后一个K分块完成后CPU读INT22结果、重新量化、存入下一层张量。沿K续算不提前量化；沿N换输出块才重新加载bias。

## 验证

```powershell
python test/int8/run_model_compiler.py --soc
```

必须使用装有依赖的Python；`--vsim`指定ModelSim路径。不加`--soc`检查编译、布局、CPU/NPU整数契约一致性和明确拒绝不支持的模型，不能替代真实SoC运行。

完整SoC用例覆盖混合网络的两个不同输入（机器码SHA相同）、强制全CPU、65→9输入分块且batch=2、9→41输出分块、INT22不安全时自动CPU Linear、CPU标量/张量减法与batch Softmax，以及工程保留的训练HAR浮点权重。逐层SBA读回核对，检查实际NPU启动任务数；模型浮点误差单独记录。训练HAR使用12个已有样本校准、另一个样本做SoC执行，不作为全测试集精度结论。

上述旧MMIO编译路径初版未修改RTL，也没有声称任意PyTorch模型都能部署；本轮新增任务引擎确实修改了NPU/DMA硬件，见 [任务架构](../report/npu_task_engine_20261117/architecture.md)。原双层专用固件及其2700拍基线保持独立，不把任意新生成程序的周期等同于该专用固件。旧版完整EDA、19例TT SDF及Lab5见 [原物理报告](../report/fc_generalization_eda_20261117/README.md)，新增硬件的验收状态见 [新报告](../report/npu_task_engine_20261117/README.md)。

本轮8组完整SoC的实测、精度边界与可启动示例包见 [验收报告](../report/model_compiler_20261117/README.md)。

编译器与运行时位于仓库顶层compiler/；独立的网络、权重和样例数据位于 [model/generic_mixed](../model/generic_mixed/README.md)。
