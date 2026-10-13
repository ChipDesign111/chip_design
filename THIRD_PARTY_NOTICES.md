# Third-party notices

本仓库包含不同来源与授权状态的组件，不能推定所有文件受同一个许可证覆盖。

| 组件 | 位置 | 来源与条款记录 |
| --- | --- | --- |
| CV32E40P / RI5CY 相关 RTL | platform/course_soc/cpu_cv32e40p | 源文件保留 ETH Zurich / University of Bologna 等版权及 Solderpad Hardware License 0.51 声明 |
| AXI、common_cells、Debug 等 | platform/course_soc/soc/rtl | 多数文件保留原 Solderpad 0.51 声明；以具体源文件头为准 |
| 平台集成与原回归材料 | platform/course_soc、verification/lab3、sw/startup/lab3、原 filelist | 提供的 Lab 3 快照；不能将上游部分文件的条款自动扩展到所有集成文件 |
| UCI HAR 及派生固定输入 | verification/vectors/har_uci24.json | UCI HAR，Reyes-Ortiz 等（2013），DOI 10.24432/C54S4K；固定文件记录 CC BY 4.0 和原行号/校验 |
| 模型导出与训练产物 | model/export、model/training | 来源与 model_version、SHA 保留；没有新增替代性的授权声明 |
| Python / 仿真 / 综合工具 | requirements.txt、外部工具安装 | 按各自发行条款使用，不将工具二进制作为源码组件分发 |

[平台 manifest](platform/course_soc/manifest.json) 标识 90 个冻结文件，版权和许可证头不做统一改写。详细来源见 [provenance](docs/provenance.md)。

## Repository licensing status

当前没有覆盖所有项目原创文件及训练产物的统一授权声明。此通知用于说明来源与边界，不授予额外权利，也不替代各文件的原条款。发布可再分发源码包前应完成组件授权清单，见 [LICENSES](LICENSES/README.md) 与 [发布流程](docs/releases.md)。

- Solderpad 0.51：源文件指向 http://solderpad.org/licenses/SHL-0.51
- UCI HAR：[数据集页面](https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones)
