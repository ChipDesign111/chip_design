# HAR MLP 模型

保留 main 的 64→32→6 训练模型、INT8 权重、偏置和量化参数。MULT=1064、SHIFT=20；数值契约见 [numerics](numerics.md)。历史全测试集整数准确率 84.9678% 是既有模型指标，不是本轮重新训练/全量验证的结果。

当前 RTL 回归已对固定 24 条六类 UCI 输入逐值比较隐藏层、六个分数和类别；完整 SoC CPU 另跑其中两个样本。数据来源、行号与哈希保存在 test/int8/har_uci24.json。硬件与整数参考一致，不表示所有分类标签都正确。

用 python tools/export_tiles.py --output tools/local/int8_tiles 导出两层 tile 权重及量化元数据。原 NPZ 按输出×输入排列，不能直接作为本设计的 DMA 内存布局。新布局见 [DMA](../report/dma.md)。读取现有导出无需 NumPy；训练需要 requirements.txt。
