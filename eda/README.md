# W8A4 SoC的TSMC180实现入口

本目录把`xzx/rtl`的完整`my_soc_top`接入Lab 4的Genus/Innovus流程。主存使用授权RA1SHD硬宏，NPU权重bank先按标准单元实现，CPU保持当前源码的时钟直通行为。系统周期20 ns是首轮目标，不是预先宣布的结果。

先读[操作指南](docs/操作指南.md)：含本机打包、服务器部署、准备、综合、01–34逐步解释、恢复和结果回传。概念不熟时查[基础知识](docs/基础知识.md)。设计相关修改与可复用部分见[实施与适配说明](docs/实施与适配说明.md)。

各文件的职责、哪些配置生效及运行产物位置见[文件结构与功能说明](docs/文件结构与功能说明.md)。

```mermaid
flowchart LR
  A[固定源码与准备] --> B[完整SoC综合]
  B --> C[按新面积规划]
  C --> D[外围与供电]
  D --> E[逻辑放置]
  E --> F[时钟树]
  F --> G[正式布线与修复]
  G --> H[最终复核与导出]
```

| 路径 | 用途 | 是否部署服务器 |
| --- | --- | --- |
| server/ | 配置、Python 3.8+命令入口、Tcl阶段与模板、验收工具 | 是，部署包自动包含 |
| package_server.py | 从当前源码构建部署专用压缩包并检查功能基线的RTL SHA | 在本机运行 |
| docs/ | 逐步操作与概念说明 | 不必上传 |
| tests/ | 自动化控制、报告解析、几何生成和部署打包的回归测试 | 开发验证用 |
| validation/ | 本次实际验证范围和记录 | 不作为设计已通过的替代证据 |
| dist/ | 生成的tar.gz及SHA，已忽略 | 上传其中部署包 |

```powershell
# Windows，在这个分支的仓库根目录
python tools/project.py check
python -m unittest discover -s eda/tests -v
python eda/package_server.py
```

生成包包含`server/`、`rtl/`、`source.json`和同源的既有功能基线；不包含PDK、厂商SRAM资料、数据集或历史EDA数据库。服务器使用`/home/almalinux/tsmc180`及课程共享目录内的授权宏资料。

复杂操作由`server/bin/eda.sh`封装。先按指南准备新工程，再可逐段运行，或用`all`执行完整流程；发生错误会停止，已通过步骤保留检查点。每个JSON只声明实际执行的检查范围；已有功能基线不是本次重新仿真，结构导出核对也不是独立工艺DRC/LVS。

脚本的实际验证状态见[验证说明](validation/README.md)。不会把原Lab 4的WNS、实例数或例外统计当成本SoC的结果。
