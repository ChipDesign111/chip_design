# PyTorch 前端与当前 INT22 RAW 后端

`frontend.py` 直接采用 main 的 `4b552b1` 版本，通过 PyTorch FX 捕获静态图并用代表输入校准对称 INT8 尺度。部署端仍使用本分支的 `RAW_INDEX=0x80`、`RAW_DATA=0x84`、`RAW_READY=0x88`，没有引入 main 的单层 FC／任务引擎 RTL。

完整 32×64 区域离线预排并由 RAW 执行，边缘由现有四项展开的 RV32IM CPU 内核计算；所有原始部分和在 CPU 中以 INT32 归约。整层结果可以超过 INT22，只要能证明 INT32 归约安全。固定权重只存一份，无运行时权重打包，也不把尾部补齐成四个常驻大块。

## 运行

Python 3.10 及以上；建议使用独立环境，原 Icarus/ModelSim 回归环境不需要安装 PyTorch。

```powershell
python -m venv tools/local/compiler_env
tools/local/compiler_env/Scripts/python -m pip install --upgrade pip
tools/local/compiler_env/Scripts/python -m pip install -r compiler/requirements.txt
tools/local/compiler_env/Scripts/python model/raw_mixed/make_fixture.py
tools/local/compiler_env/Scripts/python -m compiler --model model/raw_mixed/model.py --input test/int8/runs/raw_frontend_demo/input.npy --calibration test/int8/runs/raw_frontend_demo/calibration.npy --out test/int8/runs/raw_frontend_demo/package --simulate --vsim D:/modeltech64_2019.2/win64/vsim.exe
```

模型文件提供无参数 `build_model()` 工厂。`--factory` 可选择其他函数，`--weights weights.pth` 接收纯 state_dict，按 `weights_only=True` 加载。示例模型为固定随机权重，只验证部署，不代表训练准确率。用户模型需要提供对应结构、权重及有代表性的校准数据。

默认编译 CPU＋RAW；`--force-cpu` 使用同一量化模型和四项展开的 CPU 基线。`python -m compiler.sim PACKAGE --vsim PATH` 可单独仿真部署包。

## 支持范围与数值约定

- 输入为静态 `[B,K]`，B=1..4。batch=1 保留原路径；batch=2..4 的完整块默认调用硬件多样本 RAW，一次权重 DMA 服务所有样本。输入形状改变时重新编译。
- Linear、ReLU、ReLU6、LeakyReLU、Sigmoid、Tanh、Softmax、同形张量及标量 Add/Sub/Mul、Identity 和不改变二维形状的 reshape 等操作。Conv、Attention、广播、动态形状、未注册算子明确拒绝，不伪装为可执行 CPU 回退。
- PyTorch 图沿用 main 的有符号 INT8 张量边界，Linear 后先重定标到 INT8；CPU 激活另有其独立舍入边界。输入／权重量化采用 `rint`，定点重标定的半值向正无穷，结果饱和到 INT8。所有定点乘加与舍入中间值都在编译时证明 INT32 安全，不能证明则拒绝。量化误差与 RTL 整数实现错误分别报告。
- Sigmoid/Tanh 使用编译生成的 256 B LUT；Softmax 使用指数表和 CPU 整数归一化。校准通过不等同于全测试集准确率。
- 程序从低地址增长，数据从高地址分配，顶端 64 B 保留给计时／完成标记。总计必须在同一块 8 KiB SRAM 中；不物化第二份预排权重，不支持外部存储，也没有让 CPU 回退绕过容量限制。

## 部署包与验证

部署包包含 `firmware.hex`、小端 8192 B `firmware.bin`、`firmware.S`、`manifest.json`、`reference.json`。图程序镜像不嵌入 golden 输出；reference 仅由 testbench 和仿真后主机核对使用。

`compile_model(model.eval(), example, calibration_inputs, force_cpu=False)` 返回部署包。`package.write(directory, new_input)` 使用固定机器码和量化参数生成新输入镜像。输入形状保持一致，改变输入不会重新校准或重编译。芯片完成一次 forward 后停在 halt；持续采样或多次推理的服务循环需由应用集成。

## 多样本权重复用

batch=2..4 时，完整区域按「32 输出块 → 64 输入块 → 同块全部样本」调度。每个完整权重块仅 DMA 一次，RAW_INDEX 的高两位选择样本、低五位选择输出。CPU 分别以 INT32 累加各样本部分和，再计算紧凑右边缘和底部行，最后执行相同的有符号 INT8 重定标。

批处理使用 `B×32×4` B 的临时累加区，四样本为 512 B，在不同输出块和层之间复用；其他 CPU 层仍可复用这片空间。权重仍只保存一份，单个矩阵层的 RAW 启动数从 `B×floor(N/32)×floor(K/64)` 降为 `floor(N/32)×floor(K/64)`，有效 MAC 数和结果读回数量不变。

新路径将共享的四项展开 CPU 点积热循环对齐至 16 B，使其 80 B 循环体占五条取指缓存行；原逐样本/纯 CPU 路径的指令布局保持原样。

如果新调度的代码和缓冲无法装入 8 KiB SRAM，编译器使用相同校准结果自动重试原逐样本调度，并在 manifest 记录原因。无完整块、batch=1、`--force-cpu` 和原整数 `compile_layers` 的执行路径保持原样。每次多样本调用结束恢复硬件 batch=1。

API 可用 `compile_model(..., reuse_batch_weights=False)`，CLI 可用 `--no-batch-reuse`，显式选择原逐样本调度。manifest 的 `batch_weight_reuse`、`npu_batch`、`npu_core_starts`、`weight_dma_bytes`、`accumulator_scratch_bytes` 和 `batch_weight_reuse_fallback` 记录实际选择。

```powershell
tools/local/compiler_env/Scripts/python test/int8/run_raw_batch_reuse.py --soc --vsim D:/modeltech64_2019.2/win64/vsim.exe
```

默认比较逐样本 RAW 和多样本 RAW，可用 `--backend cpu --backend sequential --backend reuse` 加入同整数纯 CPU 对照，或用 `--case full_b4` 限定模型。边界、容量回退及实测结果见 [批处理权重复用报告](../report/raw_batch_reuse.md)。

仿真沿 Debug SBA 装载真实 SRAM，通过原 CPU、AXI、DMA、NPU 执行，逐字节检查 END 前的所有中间张量，再由 SBA 实际读回。输出 `actual_output.json` 和 `simulation.json`，不存在灌入预计算最终结果的路径。计时为实际 SRAM BEGIN/END 接受边沿，包含 CPU 初始化、调度、归约、激活和所有 DMA，排除镜像加载与仿真后核对。功能时钟为 10 ns，不代表新的物理时序签核。

图程序使用新的内存布局和量化模型，应单独测量 CPU/RAW 加速比；不能直接套用原整数测试的 9.13×、5.15×。保留整数模型入口：

```python
from compiler import compile_layers
from compiler.runtime import Layer

layers = [Layer([[1]*65 for _ in range(33)], [0]*33)]
package = compile_layers(layers, [1]*65)
package.write('test/int8/runs/my_integer_package')
```

此入口直接复用原生成器，保留 ReLU→软件64位重定标和末层 INT32 分数，自检在 END 之后。原七个模型的 CPU／优化 RAW 计时镜像必须逐字节保持原样，与 PyTorch 图的逐层有符号 INT8 契约区分。

最初接入时26次完整 SoC 的结果、原整数镜像与周期保持检查见 [前端接入报告](../report/raw_frontend.md)；批处理更新后的结果见 [权重复用报告](../report/raw_batch_reuse.md)。编译期间复制示例和校准张量，避免原地激活修改调用者的数据。图程序只记录总周期和 NPU 硬件计数，保留的软件阶段栏不作为图阶段归因。已经生成的包可在无 PyTorch 的 Python 环境中通过 `compiler.sim` 仿真。

```powershell
tools/local/compiler_env/Scripts/python test/int8/test_raw_compiler.py
tools/local/compiler_env/Scripts/python test/int8/run_raw_compiler.py --soc --vsim D:/modeltech64_2019.2/win64/vsim.exe
```
