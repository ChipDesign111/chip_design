# HAR model and reference

当前模型已经与 tiled V2 联调：官方测试集 2947 条、单/双模式共 5894 次 RTL 推理逐值一致；真实 CPU 24 条六类样例通过。流程见 [模型验证](../docs/model-verification.md)，准确率与限制见 [报告](../reports/real-model.md)。不使用 NPZ 中全为站立的 16 条样例估计总体精度。

[training/](training/README.md)：数据与浮点模型；[reference/](reference/README.md)：整数行为；[export/](export/README.md)：权重和测试向量导出。

当前基线是 UCI HAR 上的 64→32→6 MLP，参数 2278。浮点测试准确率 85.51%，INT8 权重量化、浮点激活路径为 85.10%，硬件使用的全整数路径为 84.97%。权重、特征下标和整数偏置在 [export/](export/README.md)。已实现的 [整数参考](reference/mlp_int.py) 与 NumPy 向量化参考相互核对，RTL 逐值对照该整数契约。
