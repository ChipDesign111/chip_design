# W8A4 部署配置

[w8a4.json](w8a4.json) 是最终部署参数：INT8权重、有符号INT4输入、ReLU后UINT4、INT32累加和偏置。权重和64个特征索引复用model/export；本文件冻结新偏置与重定标参数，不覆盖INT8基线。

输入按 `clip(round(x / input_scale), -7, 7)` 打包，每个32 bit字包含8个低位优先的4 bit值。隐藏值为 `min(15, (max(acc,0)*39986 + 8388608) >> 24)`。完整2947条准确率2490/2947；原INT8为2504/2947。该测试划分曾用于原checkpoint选择，不是独立盲测。

参数与测试由统一入口加载，详见 [设计与验证](../../report/streaming.md)。
