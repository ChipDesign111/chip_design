# 算法与参考

[training/](training/README.md)：数据与浮点模型；[reference/](reference/README.md)：整数行为；[export/](export/README.md)：权重和测试向量导出。

当前基线是 UCI HAR 上的 64→32→6 MLP，参数 2278。浮点测试准确率 85.51%，INT8 权重量化后 85.10%。权重、特征下标和整数偏置在 [export/](export/README.md)。整数参考程序仍待写，RTL 对照以 `quant_params.json` 里的规则为准。
