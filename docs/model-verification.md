# 已选 HAR 模型如何在 RTL / SoC 验证

2026-10-13。来源是已合入 main 的 PR #2，模型版本 har-mlp-64x32x6-2026-09-24。保留原训练文件、浮点/INT8 权重、量化参数和指标，没有重新训练或替换参数。

## 从文件到加速器

1. weights_int8.npz：取 fc1_weight_int8[32,64]、fc2_weight_int8[6,32]，NPZ 禁止 pickle。
2. quant_params.json：取两层 INT32 偏置、MULT=1064、SHIFT=20；舍入加数为 524288，与 RTL 契约完全一致。
3. meta.json：固定训练时选择的 64 个特征下标和标签。只应用这些下标，不在测试集重新选特征。
4. UCI test/X_test.txt：561 维取对应 64 维，按保存的输入尺度量化为 INT8。
5. NumPy INT64 向量化实现与现有逐标量 Python infer 独立计算全部 hidden/score/class，并逐值互相核对。
6. 相同权重按输出行优先、低字节优先打包，经 MMIO 装入 NPU；计算与存储 RTL 无需修改。
7. RTL 逐值对照；CPU 自检则在真实 CV32E40P 中通过固定 AXI 外围装载、启动和读回。

导出器核对浮点权重与 INT8 量化结果、偏置尺度、特征下标/输入尺度的一致性。对任意 INT8 输入的保守累加绝对界：第一层 254949、第二层 153167，均远小于 INT32 上限。

标签为 0 步行、1 上楼、2 下楼、3 坐、4 站立、5 躺卧。原 NPZ 的 16 条样例全是站立，不能代表六类或总体准确率。

## 三层证据

| 层级 | 数据和判定 |
| --- | --- |
| 算法准确率 | 官方 UCI 测试集全部 2947 条，对真实标签评估浮点、权重量化和全整数版本 |
| RTL 计算正确性 | 全部 2947 条各运行单次和双样本模式，共 5894 次；每个 hidden/score/class 均须与整数参考一致 |
| 真实 CPU / SoC | 六类各 4 条，共 24 条，12 个双样本批次；逐值比较两层结果、类别、周期及重叠计数 |

RTL 的判定目标是整数参考，不直接把真实标签当成“硬件应该算出的答案”。模型预测错标签而 RTL 与参考相同，属于模型误差。
24 条样例按每类等间隔测试行确定，不依赖预测正确与否；小样本准确率不替代全测试集。

## 可运行命令

需要 NumPy；推理/验证无需 Torch，无需解包执行 best.pt。

```text
python -m pip install numpy==2.3.5
python scripts/download_uci_har.py
python scripts/run_model_tests.py --data-root "data/UCI HAR Dataset" --vsim "本机 vsim 路径"
```

原始官方下载、提取数据及 SHA 位于被忽略的 data/。完整模型向量、程序、日志、结果在 build/real_model/、build/logs/。

不下载数据集时，可用已提交的六类 24 条真实 INT8 输入做快速复现：

```text
python scripts/run_model_tests.py --unit
python scripts/run_model_tests.py --vsim "本机 vsim 路径"
```

CI 使用第一条（24 条各跑单次/双次，共 48 推理），本机另有全 2947 条测试的记录。完整 SoC 使用原 my_soc_tb，不改原课程测试；24 条 CPU 程序只占 6232 B，不超 8 KB 主 SRAM。

需要重新生成小样本固定文件时：
python scripts/export_real_model.py --data-root "data/UCI HAR Dataset" --write-fixture
先检查来源、特征和 SHA，不能为了迎合错误输出更改参考。

## 数据来源和适用范围

原数据来自 [UCI HAR](https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones)，引用 Reyes-Ortiz 等（2013），DOI 10.24432/C54S4K；24 条派生样例在 verification/vectors/har_uci24.json 保留来源、CC BY 4.0 标记、原始行号、特征下标及源文件 SHA。原始大数据不入库。

当前模型训练时按测试集挑选 best checkpoint，本次是对其原测试划分复测，不是额外独立盲测，也不声称本次重新训练。FPGA/ASIC、实际频率与功耗未验证。结果见 [真实模型报告](../reports/real-model.md)。
