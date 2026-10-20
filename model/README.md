# 最终部署模型

| 文件 | 用途 |
| --- | --- |
| [weights.npz](weights.npz) | 仅含fc1_weight_int8、fc2_weight_int8与64个feat_idx |
| [quantization/w8a4.json](quantization/w8a4.json) | 最终偏置、输入尺度、隐藏重定标和准确率 |
| [deployment.json](deployment.json) | 结构、类别顺序、来源与部署权重SHA |
| [reference/mlp.py](reference/mlp.py) | 独立标量整数金标准 |
| [numerics.md](numerics.md) | 精确数值和打包规则 |

MLP为64→32→6。全2947条原测试集正确2490条（84.4927%）。原checkpoint使用过该测试划分选优，因此不是独立盲测。硬件逐值一致不代表每条分类正确。

当前分支仅保存部署所需资料。训练脚本、checkpoint、浮点导出和旧INT8激活数值契约已保存在仓库外归档，见 [管理说明](../report/local_archive.md)。运行部署测试无需PyTorch。数据集下载到忽略的model/data：`python tools/project.py download-data`；全量验证用 `test --suite unit --data-root "model/data/UCI HAR Dataset"`。
