# Changelog

## Unreleased — 2026-10-15

- 顶层业务目录统一为 rtl / fpga / model / eda / test / report / tools。
- 完整 SoC 收入 rtl；仅保留当前 HAR NPU，删除原 NPU、4×4 测试及旧导入入口。
- 默认主存统一为 portable-sram，授权环境可选 ra1shd；旧 reference 配置移除。
- 测试按日期归档，每次运行独立保留脚本快照、源 SHA、结果和报告；工具入口改为 python tools/project.py。
- 厂商资料移至 tools/local；fpga 与 eda 保持空占位。

## Prior baselines

2026-10-13：tiled MLP、真实模型及工程化验证。2026-10-15：主 SRAM 宏功能接入。具体实测记录按日期见 [test](../test/README.md)。
