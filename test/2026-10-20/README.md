# 2026-10-20

- [连续流水RTL验证](stream/report.md)：保留FC1 32×4、FC2 6×2和32路重定标，DMA与计算重叠；三种模式公平测量。
- [精度结果](precision/results.json)：7352条训练输入校准、2947条测试输入评估，W8A4参数单独冻结。
- [24条金标准](precision/w8a4_soc24_gold.json)：原六类固定测试行，按新输入尺度量化，包含32个hidden、6个score和类别。

可复用测试在scripts/、rtl/，每次运行的完整日志、源SHA和脚本快照保存在忽略的runs/目录。公开证据只保留数值摘要，不包含厂商文件或编译数据库。完整设计见 [streaming.md](../../report/streaming.md)。
