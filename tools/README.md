# Tools

project.py：统一入口；check_repo.py：目录/链接/配置检查；check_hardware.py：保留外围校验；workspace.py：日期与独立测试记录；memory_profile.py：主存选择；download_uci_har.py：官方数据下载。

测试/固件生成/模型导出/通用综合脚本归 test/2026-10-15/scripts。临时工具与授权 SRAM 原始资料归 tools/local，整个目录忽略。完整 SoC 的 ASIC 工艺综合和前后仿入口见 [EDA](../eda/README.md)，生成证据归忽略目录 `eda/work/`；FPGA 仍为空占位。使用见 [开发说明](../report/development.md)。

DMA: project.py test --suite dma-unit runs protocol/ingress checks; --suite dma runs matched real-model CPU/DMA SoC benchmarks. See [DMA](../report/dma.md).
