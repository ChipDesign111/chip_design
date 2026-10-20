# 最终 W8A4 数值契约

权重形状为fc1=(32,64)、fc2=(6,32)，按输出行排列，均为INT8。选中的64维原始特征按 `clip(round(x/input_scale),-7,7)` 量化；input_scale=1/7，round使用最近偶数规则。

FC1以INT32累加权重×输入并加INT32偏置；ReLU后隐藏值为 `min(15,(max(acc,0)*39986+8388608)>>24)`。隐藏值UINT4、范围0..15；FC2乘以INT8权重并加INT32偏置，输出6个INT32得分。Argmax平局取最小下标。偏置以 [w8a4.json](quantization/w8a4.json) 为准。

每条输入64个4 bit二补码值，低维先放低位，每32 bit字8维，共8字/32 B。内部tile使用扩展后的8 bit数值。权重按每字4个INT8值、低维先放低字节，共560字；随后32个FC1偏置和6个FC2偏置，合计598字。M与SHIFT另写寄存器。

类别顺序以 [deployment.json](deployment.json) 为准；标量金标准在 [reference/mlp.py](reference/mlp.py)。
