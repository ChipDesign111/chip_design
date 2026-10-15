# 参数与向量导出

| 文件 | 内容 |
| --- | --- |
| [weights_float32.npz](weights_float32.npz) | 浮点权重和偏置 |
| [weights_int8.npz](weights_int8.npz) | 对称 INT8 权重、float32 偏置、输入尺度、16 条样例 |
| [quant_params.json](quant_params.json) | 整数偏置、隐藏层重新量化系数、标签顺序 |
| [meta.json](meta.json) | 结构、特征下标、类别名、浮点准确率 |
| [metrics.json](metrics.json) | 训练曲线和分类报告 |

`weights_int8.npz` 的权重按 PyTorch `Linear` 的 `(out, in)` 排列。`sample_x_int8` 的 16 条都来自测试集开头，标签全是「站」，不能拿来估计总体准确率。

浮点前向：

```text
x = x_int8 * input_scale
h = relu(W1_int8 * W1_scale @ x + b1_float)
z = W2_int8 * W2_scale @ h + b2_float
class = argmax(z)
```

整数前向见 [quant_params.json](quant_params.json)：INT32 累加，ReLU 后用 `(acc * 1064 + 524288) >> 20` 压回 0–127，再做第二层。该整数路径在测试集上的准确率是 84.97%。平局时取最小下标。

现已通过 test/2026-10-15/scripts/export_real_model.py 从真实测试输入导出完整 hidden/score/class 到 test/日期/runs/时间戳/real_model，NumPy 与逐标量参考逐值一致；RTL 单/双模式及真实 CPU 已验证。命令与可复现固定样例见 [开发说明](../../report/development.md)。原参数文件保持不变。
