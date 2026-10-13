# 数据与训练

模型已经训完。结构是 `Linear(64, 32)` → ReLU → `Linear(32, 6)`，参数 2278。检查点在 [checkpoints/best.pt](checkpoints/best.pt)。

## 数据

使用 [UCI HAR](https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones)。每个窗口原有 561 维加速度计和陀螺仪特征。训练集上用 ANOVA F 值选出 64 维，下标在 [../export/meta.json](../export/meta.json) 的 `selected_feature_indices`。原始数据集大约 60 MB，不入库；下载后解压到仓库根目录的 `data/UCI HAR Dataset/`（该目录已被忽略）。

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

## 复现

```bash
python -m venv .venv
source .venv/bin/activate
pip install torch numpy scikit-learn
python model/training/train_har_mlp.py --epochs 80 --batch-size 128 --lr 1e-3
```

多卡机器可以用 `model/training/run_train.sh`，它只占用 `nvidia-smi` 里当前较空的一张卡。优化器是 Adam，学习率 `1e-3`，权重衰减 `1e-4`，损失是交叉熵。

Davide Anguita 等，*A Public Domain Dataset for Human Activity Recognition Using Smartphones*，ESANN 2013。
