# 服务器部署文件

这个目录是部署专用程序，但单独上传它还不够：需要同版本`rtl/`及`source.json`。在仓库根目录运行`python eda/package_server.py`生成完整部署包，按仓库`eda/docs/操作指南.md`上传和解压。查结果与原始报告的方法见仓库`eda/docs/报告查找与分析.md`；这些文档不随部署包上传。

课程PDK在`/lec/pdk/tsmc180`，宏资料在`/lec/lab4`。默认design.json已使用共享PDK路径；先复制一份配置，设置实际可读的pdk_root和macro_source，再在第一次prepare/all传`--config /完整路径/design.json`。不要直接改已被source.json记录SHA的部署文件。

服务器使用Python 3.8+标准库，不要求安装仓库功能测试使用的NumPy、Icarus、Yosys或ModelSim。功能测试应在相应环境另外运行并核对源码SHA。

```sh
# 解压包根目录包含server/和rtl/；先按主指南设置EDA_CONFIG为配置副本
bash server/bin/eda.sh prepare --work "$EDA_WORK" --config "$EDA_CONFIG"
bash server/bin/eda.sh doctor --work "$EDA_WORK"
bash server/bin/eda.sh elaborate --work "$EDA_WORK"
bash server/bin/eda.sh synth --work "$EDA_WORK"
bash server/bin/eda.sh size --work "$EDA_WORK"
bash server/bin/eda.sh pnr --work "$EDA_WORK" --until 14
bash server/bin/eda.sh pnr --work "$EDA_WORK" --until 26
bash server/bin/eda.sh pnr --work "$EDA_WORK" --until 34
bash server/bin/eda.sh report --work "$EDA_WORK"
bash server/bin/eda.sh package --work "$EDA_WORK"
```

全流程入口为`bash server/bin/eda.sh all --work <新目录>`；它执行准备、doctor、综合、后端和报告。已准备过的工程可用同一命令继续已通过的步骤；输入身份变化则拒绝续跑。这个固定profile只覆盖文档中六路信号、一个RA1SHD主存和当前W8A4 SoC。

配置必须在准备之前确定：复制`config/design.json`到自己的配置文件，修改后通过`--config /完整路径/design.json`传给prepare或第一次all。使用默认配置时不需该参数。修改已准备工程的输入会触发保护，应重新准备新目录。

`config/`是当前设计的正式参数、库配置与SDC，`syn/scripts/`是正式Genus流程，`pnr/scripts/`是正式Innovus初始化和分析视图。prepare直接复制这些文件并写入本轮路径与参数；不再依赖参考模板。`tcl/steps/`按讲义保存后端动作，运行时按实际几何生成`pnr/generated/`。不要绕过入口直接source步骤文件。

GUI截图使用当前DISPLAY，或自动申请100–199间一个空闲Xvfb显示；只回收本次启动的Xvfb。无图形环境可加`--headless`，执行范围相同但不生成截图。日志和JSON必须保留；完整签核范围见操作指南。

第32步会读取当前扇出明细，对普通单驱动网络插非反相缓冲分支；保留原天线二极管，重新布线和提取RC，再按同一约束复核。不会提高扇出限制或放宽时钟。详细步骤、支持范围和失败处理见操作指南。

完整package之后，可用`bash server/bin/review.sh --work <本轮工作目录>`生成review_delivery.tar.gz、校验文件和review_manifest.json。轻量包保留配置、源文件、阶段证据、报告、截图和gzip层次网表，大型DEF/GDS/flat网表/SPEF/SDF留远端并记录SHA及大小。review.sh使用部署程序收集结果，验证本轮冻结控制程序的输入与库身份，不改已有工程输入。

下载并校验后，使用`bash server/bin/eda.sh clean --work <本轮工作目录> --dry-run`预览；去掉`--dry-run`执行。只清理已知交付压缩包、校验文件、`.part`和压缩网表暂存副本，保留清单、报告、日志、所有中间文件、检查点和最终视图。新部署入口可对旧工程执行该清理，无需改变旧工程输入；流程锁被占用时拒绝清理。不会遍历其他工程或主目录压缩包。

打包先写`.part`，完整写入后替换正式包；review自动清理自己的暂存网表与未完成包。原始上传包保留在该版本根目录，作为来源，不由clean删除。

所有服务器文件统一放在`~/Desktop/fullstack_chipdesign`。公共脚本是顶层unpack.sh；每次上传必须新建uploads下的独立目录，原包放在该目录。公共解压器调用本版本的workspace.sh，生成该目录自己的README.html、run_env.sh和run_all.sh。后续脚本、配置、work、日志、结果都属于本上传目录，不使用全局deploy/runs或当前版本指针。
