# 服务器部署文件

这个目录是部署专用程序，但单独上传它还不够：需要同版本`rtl/`及`source.json`。在仓库根目录运行`python eda/package_server.py`生成完整部署包，按仓库`eda/docs/操作指南.md`上传和解压。

服务器使用Python 3.8+标准库，不要求安装仓库功能测试使用的NumPy、Icarus、Yosys或ModelSim。功能测试应在相应环境另外运行并核对源码SHA。

```sh
# 解压包根目录包含server/和rtl/；替换为自己的新工程路径
bash server/bin/eda.sh prepare --work "$HOME/chip_eda_runs/w8a4_run01"
bash server/bin/eda.sh doctor --work "$HOME/chip_eda_runs/w8a4_run01"
bash server/bin/eda.sh elaborate --work "$HOME/chip_eda_runs/w8a4_run01"
bash server/bin/eda.sh synth --work "$HOME/chip_eda_runs/w8a4_run01"
bash server/bin/eda.sh size --work "$HOME/chip_eda_runs/w8a4_run01"
bash server/bin/eda.sh pnr --work "$HOME/chip_eda_runs/w8a4_run01" --until 14
bash server/bin/eda.sh pnr --work "$HOME/chip_eda_runs/w8a4_run01" --until 26
bash server/bin/eda.sh pnr --work "$HOME/chip_eda_runs/w8a4_run01" --until 34
bash server/bin/eda.sh report --work "$HOME/chip_eda_runs/w8a4_run01"
bash server/bin/eda.sh package --work "$HOME/chip_eda_runs/w8a4_run01"
```

全流程入口为`bash server/bin/eda.sh all --work <新目录>`；它执行准备、doctor、综合、后端和报告。已准备过的工程可用同一命令继续已通过的步骤；输入身份变化则拒绝续跑。这个固定profile只覆盖文档中六路信号、一个RA1SHD主存和当前W8A4 SoC。

配置必须在准备之前确定：复制`config/design.json`到自己的配置文件，修改后通过`--config /完整路径/design.json`传给prepare或第一次all。使用默认配置时不需该参数。修改已准备工程的输入会触发保护，应重新准备新目录。

`template/`是带来源注释的课程流程适配基础；`tcl/steps/`按讲义保存操作。执行入口会把它们变换到工程`pnr/generated/`：适配工作目录、当前宏实例、实际裸片尺寸、PAD映射与动态检查。不要绕过命令入口直接source原步骤文件。

GUI截图使用当前DISPLAY，或自动申请100–199间一个空闲Xvfb显示；只回收本次启动的Xvfb。无图形环境可加`--headless`，执行范围相同但不生成截图。日志和JSON必须保留；完整签核范围见操作指南。
