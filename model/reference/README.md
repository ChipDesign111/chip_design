# 整数参考模型

[mlp_int.py](mlp_int.py) 实现与 [数值规则](../../docs/numerics.md) 一致的两层网络，返回 hidden、scores、class。实现使用 Python 整数，显式检查 INT8 操作数、维度、量化配置与 INT32 累加范围。

合成边界向量及真实模型均使用此参考。真实模型导出还使用独立 NumPy INT64 路径逐值核对；RTL 再比较每个隐藏值、得分和类别。舍入、饱和与 Argmax 平局规则属于接口契约。
