# W8A4 SoC 的服务器 EDA 流程

本目录只维护部署所需文件、正式 Genus/Innovus 流程、操作说明和实际结果分析。当前设计是完整 `my_soc_top`，主存采用 RA1SHD 硬宏，NPU 权重 bank 首轮按标准单元实现。

按[操作指南](docs/操作指南.md)从本机打包、上传服务器开始，依次完成配置、综合、后端 01–34、报告分析与结果回传。每阶段说明文件作用、执行位置、命令和完成标志。已有结果见[结果与分析](results/README.md)，读报告方法见[报告查找与分析](docs/报告查找与分析.md)。

```text
eda/
├── package_server.py  生成服务器部署包
├── server/            正式配置、综合/后端脚本和运行模块
├── docs/              操作、34步解释、报告分析、基础知识
└── results/           实测结果、原始报告、布局图和分析
```

在 Windows 仓库根目录生成部署包：

```powershell
python eda/package_server.py
```

将 `eda/dist/chip_design_eda.tar.gz` 与对应 `.sha256` 上传，解压后包含 `server/`、`rtl/`、`source.json`。不包含 PDK、授权 SRAM、开发自检、临时工具或历史数据库。课程 PDK 在 `/lec/pdk/tsmc180`，SRAM 资料在 `/lec/lab4`。

`server/config/` 是本设计的正式配置，`server/syn/scripts/` 是直接使用的综合脚本，`server/pnr/scripts/` 是直接使用的后端初始化/分析脚本；没有参考模板目录。`server/tcl/steps/` 组织讲义的 34 个操作，`bin/eda.sh` 负责调用。

首次运行可分段观察，也可用 `all` 连续完成；同一工程支持正常断点续跑。阶段的时序、DRC、天线、供电/信号连接和导出核对属于正式 EDA 验收，保留在流程中。开发者单元测试、兼容性试验、检查点导入助手和原始参考资料只保留在本地工作区。

完整文件作用见[文件结构与功能说明](docs/文件结构与功能说明.md)。本流程覆盖单 TT 教学实现，独立晶圆厂签核和 SDF 回标仿真需另行执行。

结果下载校验后，`bash server/bin/eda.sh clean --work "$EDA_WORK" --dry-run`可预览重复压缩包及打包暂存文件，去掉`--dry-run`执行；保留中间文件、检查点、报告与最终视图。具体范围见操作指南第10.1节。
