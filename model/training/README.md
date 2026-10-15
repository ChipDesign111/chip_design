# 数据与训练

已提交模型结构为 `Linear(64, 32)` → ReLU → `Linear(32, 6)`，参数 2278。训练检查点为 [checkpoints/best.pt](checkpoints/best.pt)，推理和 RTL 验证使用 [导出参数](../export/README.md)，不需要加载检查点。

## 数据

使用 [UCI HAR](https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones)。每个窗口原有 561 维加速度计和陀螺仪特征。训练集上用 ANOVA F 值选出 64 维，下标在 [../export/meta.json](../export/meta.json) 的 `selected_feature_indices`。原始数据集大约 60 MB，不入库；下载后解压到`model/data/UCI HAR Dataset/`（该目录已被忽略）。

标签与 UCI HAR 的 `y - 1` 一致：

| 下标 | 类别 |
| --- | --- |
| 0 | 步行 WALKING |
| 1 | 上楼 WALKING_UPSTAIRS |
| 2 | 下楼 WALKING_DOWNSTAIRS |
| 3 | 坐 SITTING |
| 4 | 站 STANDING |
| 5 | 躺 LAYING |

坐和站是主要混淆来源。

## 训练入口

下列命令用于重新训练。原训练依赖尚未锁定，不能承诺跨版本得到相同权重；当前验证基线以已提交参数及 SHA 为准。原脚本使用测试划分选择最佳 checkpoint，其报告不属于额外独立盲测。后续训练应增加独立验证划分，再对保留测试集做最终评估。

```bash
python -m venv .venv
source .venv/bin/activate
pip install torch numpy scikit-learn
python model/training/train_har_mlp.py --epochs 80 --batch-size 128 --lr 1e-3
```

GPU 环境可使用 [run_train.sh](run_train.sh)，脚本通过 `nvidia-smi` 选择空闲程度较高的单张卡。优化器为 Adam，学习率 `1e-3`，权重衰减 `1e-4`，损失为交叉熵。重新训练或更换特征必须更新导出参数、来源、固定向量和验证报告。

Davide Anguita 等，*A Public Domain Dataset for Human Activity Recognition Using Smartphones*，ESANN 2013。
