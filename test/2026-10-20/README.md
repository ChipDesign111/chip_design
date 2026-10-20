# 最终 W8A4 连续流水交付

- [设计说明](../../report/streaming.md)：最终硬件、DMA、寄存器及复现命令。
- [量化配置](../../model/quantization/w8a4.json)：唯一部署配置，不包含候选精度实验。
- [24条金标准](fixtures/w8a4_soc24.json)：相同UCI样本的输入、hidden、score和类别。
- [版本比较](version-compare/report.md)：前一版真实RTL与最终版完整SoC，双SRAM后端。
- [验证结果](validation.json)：最终配置的协议、全模型和结构检查。

`scripts/run_stream_tests.py` 验证最终NPU及DMA；`scripts/run_version_compare.py` 是唯一SoC性能基准；`scripts/check_stream_synthesis.py` 检查结构。统一运行 `python tools/project.py test --suite stream --vsim /path/to/vsim`，需要全2947条时加 `--data-root`。原始日志和仿真数据库只生成到忽略的runs目录，不提交仓库。
