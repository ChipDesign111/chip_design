# Tests by date

| 日期 | 内容 |
| --- | --- |
| 2026-10-08 | 初始功能验证历史记录 |
| 2026-10-13 | tiled、真实模型和工程入口历史记录 |
| [2026-10-15](2026-10-15/README.md) | SRAM 接入、当前验证脚本/TB/固定输入与目录迁移验证 |
| [2026-10-20](2026-10-20/README.md) | 可选W8A4连续流水RTL、全模型逐值对照与DMA/SoC性能 |

每个测试案例放在日期下，保存脚本身份、结果 JSON 和 report.md。当前可复用脚本在 2026-10-15/scripts，testbench 在 rtl，24 条真实输入在 fixtures。后续新增测试在新日期目录组织，并更新统一入口的测试版本选择。

每次运行自动生成同一天的 runs/时间戳目录：脚本快照、testbench、tools、源 SHA manifest、results、logs、report.md 均独立保存。大产物默认不入 Git，CI 以 artifact 保留公开运行证据；提交时归档精简案例结果。

历史 JSON 不改写旧路径或 SHA；历史报告不证明当前版本通过。旧 NPU 设计与其专用脚本/镜像已删除，Git 历史仍可追溯当时源码。
