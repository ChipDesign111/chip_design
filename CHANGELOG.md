# Changelog

本文件记录面向使用者的行为、接口与工程流程变化。未发布内容保留在 Unreleased；正式版本及证据按 [发布流程](docs/releases.md) 管理。

## Unreleased

### Added

- 跨平台 project.py 入口：环境诊断、仓库检查、验证套件、通用综合和本地 CI。
- 锁定的模型验证依赖、EditorConfig、分层 CI 与失败日志/结果归档。
- ADR、发布检查、组件声明、工程路线图和缺陷/功能提案模板。

### Changed

- README 与现行文档按架构、契约、验证和交付状态组织。
- 早期排期、协作和辅助开发记录移至 docs/archive；历史验证保留 reports/history。
- 原“scaffold”检查更新为仓库策略、链接、Python 语法和配置检查。

### Compatibility

- 加速器 RTL、MMIO ABI、数值规则、训练权重及 90 个冻结文件保持不变。
- 原后端脚本入口继续可用，project.py 作为推荐入口。
- 既有数值结果属于记录时的验证基线；工程流程变化不改写历史证据。
