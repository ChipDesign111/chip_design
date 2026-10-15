# Component provenance

## 固定参考平台

platform/course_soc 基于提供的 Lab 3 SoC_cv32e40p 快照，包含已完成四端口 NPU 接入的外围。该快照不声明等同未经修改的上游发行包。

[manifest.json](../platform/course_soc/manifest.json) 对 CPU、互连、Debug、复位、存储、原 TB/C/hex/启动和 filelist 共 90 文件记录来源相对路径及原字节 SHA-256。Git 不转换这些文件行尾。

平台更新使用独立变更，记录获取来源、差异、版权/许可证、校验迁移和完整回归。加速器实现与冻结平台分别维护。

## 模型与数据

model/export 保存 64→32→6 HAR 模型的浮点/INT8 产物、特征下标、量化参数和历史指标。模型身份由文件 SHA 和 quant_params 的 model_version 标识，验证无需执行 pickled checkpoint。

数据源为 [UCI HAR](https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones)，引用 Reyes-Ortiz 等（2013），DOI 10.24432/C54S4K。24 条固定派生输入保留来源、原行号、CC BY 4.0 标记、特征下标及源文件 SHA。完整下载数据只保存在忽略的 data/。

训练流程使用原测试划分选择最佳 checkpoint，当前准确率复测不等于额外独立盲测。报告保留此评估边界。

## 授权与记录

组件按其原始条款管理；没有以仓库结构变更统一替换许可证。见 [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md) 和 [LICENSES](../LICENSES/README.md)。

早期来源调查、课程规划和辅助开发记录保留在 [历史归档](archive/README.md)，不作为当前接口或工具版本的权威说明。

## 本地主 SRAM 资料

RA1SHD 原始模型与物理视图作为授权本地依赖移入忽略的 asic/vendor，公开仓库只包含项目编写的适配接口与测试。原始资料不纳入 90-file 平台 manifest，不上传到公共 CI。见 [SRAM](sram.md)。
