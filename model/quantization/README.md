# 最终量化参数

[w8a4.json](w8a4.json) 是唯一部署量化配置：INT4输入、UINT4隐藏、INT8权重和INT32偏置/累加。部署权重与特征索引来自 [weights.npz](../weights.npz)。精确公式见 [数值契约](../numerics.md)。此目录不包含候选精度实验或旧INT8激活配置。
