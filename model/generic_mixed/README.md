# 通用神经网络与数据测试样例

这是固定随机权重的合成部署样例，用于验证自动分块及CPU/NPU混合执行，不是训练模型，也不用于评估分类准确率。原有HAR模型的训练、导出和数值契约不变。

网络定义在[model.py](model.py)：输入17维→Linear(17,12)→ReLU/Sigmoid/乘法/残差加法→Linear(12,5)→标量乘加→Softmax。Linear自动使用NPU，其余运算使用CPU。`build_model()`是编译器入口工厂。

## 固定数据

| 文件 | 用途 |
| --- | --- |
| [weights.pth](data/weights.pth) | PyTorch纯state_dict，固定种子42，实际验证使用这份权重 |
| [input.npy](data/input.npy) | 主输入，float32，[1,17] |
| [calibration.npy](data/calibration.npy) | 两组代表性校准数据，[2,1,17] |
| [held_out.npy](data/held_out.npy) | 另一组输入，用于验证同一机器码处理不同数据 |
| [expected_float.npy](data/expected_float.npy) | 主输入的原始PyTorch浮点输出，[1,5] |
| [held_out_expected_float.npy](data/held_out_expected_float.npy) | 另一组输入的浮点输出 |
| [manifest.json](data/manifest.json) | 种子、形状、依赖版本与每份数据的SHA-256 |

held_out没有作为独立校准样本加入；它与校准样本是人工相关构造，不是统计意义上的独立盲测集。整数输出由编译器的固定量化规则决定，应与SoC逐值比较；浮点参考用于单独衡量量化误差。

## 从样例编译并运行

在仓库根目录、已安装[编译器依赖](../../compiler/requirements.txt)的环境中：

```powershell
python -m compiler --model model/generic_mixed/model.py --weights model/generic_mixed/data/weights.pth --input model/generic_mixed/data/input.npy --calibration model/generic_mixed/data/calibration.npy --out test/int8/runs/generic_mixed --simulate
```

此命令生成机器码和权重镜像，并在完整SoC RTL中运行。去掉`--simulate`只生成部署包。另一组输入可将`--input`改为held_out.npy，但若要求量化参数和机器码完全固定，应编译一次后使用Python API的`package.write()`替换输入，回归测试采用这种方式。

编译器、CPU内核、运行时位于顶层[compiler](../../compiler/README.md)；本目录只包含网络和测试数据。
