# HAR MLP

64→32→6 MLP，2278 参数。training 保存训练脚本与 checkpoint，export 保存原始浮点/INT8 权重、特征下标、量化参数和历史指标，reference 保存精确整数实现。既有权重与量化参数不因目录重组改变。

输入为加速度计/陀螺仪窗口预处理后的 64 个 INT8 特征；标签为 0 步行、1 上楼、2 下楼、3 坐、4 站立、5 躺卧。当前 MULT=1064、SHIFT=20，算术见 [numerics.md](numerics.md)。

历史全 2947 条测试：浮点 85.5107%，权重量化/浮点激活 85.1035%，全整数 84.9678%。RTL 单/双模式 5894 次逐值一致；详细证据在 [真实模型历史记录](../test/2026-10-13/real-model/report.md)。当前 24 条六类样例用于 SoC 集成，18 条分类正确；硬件逐值一致不代表分类全部正确。

原训练用测试划分选最佳 checkpoint，因此不是额外独立盲测。验证导出权重无需加载 best.pt；NumPy 使用 requirements.txt。原始数据下载到忽略的 model/data。运行：python tools/project.py test --suite model 或 --suite model-soc。

可选 [W8A4连续流水RTL](../report/streaming.md) 使用单独冻结的偏置、M=39986、SHIFT=24，输入INT4、隐藏UINT4、权重INT8。原export保持不变；新参数见 [最终量化配置](../model/quantization/w8a4.json)。完整2947条低位宽RTL逐值验证及24条真实CPU/SoC验证见 [新报告](../test/2026-10-20/version-compare/report.md)。
