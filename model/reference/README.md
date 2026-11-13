# Integer reference

mlp_int.py 使用 Python 整数实现两层 MLP，显式检查 INT8 范围、维度、量化配置和 INT22 补码累加。真实模型另有 NumPy INT64 独立路径互相核对；RTL 比较全部符号扩展后的 score、hidden 和类别。完整契约见 [numerics](../numerics.md)。
