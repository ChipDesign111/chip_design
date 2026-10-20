# Changelog

## RTL layout — 2026-10-20

- rtl收拢为soc/platform/npu/dma；共享tile和bank进入npu/common，INT8兼容代码进入baseline。
- 编译清单、测试/综合源列表、外围manifest和行尾规则同步迁移，所有SV/SVH内容保持原字节。
- 重写各层README，明确W8A4最终版与默认INT8配置、阅读顺序、修改边界和验证入口。

## Streaming profile — 2026-10-20

- 新增可选W8A4连续流水RTL，保持FC1 32×4、FC2 6×2和32路并行重定标；原INT8模块不改写。
- 新增带信用和成功提交的输入DMA，最多两帧/突发，支持1～64帧批次。
- 相对前一版真实RTL，在相同CPU类别校验口径下，整机13619→4972周期（2.739×），权重装载后11404→3314周期（3.441×）。
- 交付仅保留最终W8A4配置、必要验证与版本比较，移除精度候选、内部模式实验和重复SoC测试。
- 完整2947条低精度RTL逐值对照、248项DMA协议检查、双SRAM完整SoC及默认INT8回归通过。见 [设计](streaming.md)、[证据](../test/2026-10-20/version-compare/report.md)。

## Unreleased — 2026-10-15

- 顶层业务目录统一为 rtl / fpga / model / eda / test / report / tools。
- 完整 SoC 收入 rtl；仅保留当前 HAR NPU，删除原 NPU、4×4 测试及旧导入入口。
- 默认主存统一为 portable-sram，授权环境可选 ra1shd；旧 reference 配置移除。
- 测试按日期归档，每次运行独立保留脚本快照、源 SHA、结果和报告；工具入口改为 python tools/project.py。
- 厂商资料移至 tools/local；fpga 与 eda 保持空占位。

## Prior baselines

2026-10-13：tiled MLP、真实模型及工程化验证。2026-10-15：主 SRAM 宏功能接入。具体实测记录按日期见 [test](../test/README.md)。

## DMA integration

新增独立 AXI burst DMA，用于主 SRAM 到 NPU 参数/输入装载；最多 16-word 缓冲，新增 0xD00 CSR。显式更新两个 SoC 集成文件及其来源记录，保持算术核心和原寄存器兼容。增加协议、并发、错误、复位与真实模型端到端周期对比。见 [DMA](dma.md)。
