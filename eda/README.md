# 从本机打包到服务器EDA，再回传查看结果

本目录实现当前分支完整my_soc_top的Genus综合与Innovus讲义01–34步。每次上传都创建一个新目录；服务器只共用顶层unpack.sh解压器，配置、脚本、work、日志和结果全部属于各自上传版本。

环境检查、EDA、结果整理是三个独立服务器脚本。本机总控可以依次调用它们，等待完成并抓取、校验、解压结果。以下使用已有SSH别名chipdesign。

## 1．本机准备

Windows PowerShell，先进入当前分支仓库根目录：

```powershell
Set-Location 'C:\Users\zixiang\OneDrive\Desktop\advanced_chip_study\tmp\npu-stream-rtl'
git branch --show-current
git status --short
python --version
ssh -o ClearAllForwardings=yes -o BatchMode=yes chipdesign 'printf "SSH connected\n"'
```

分支应为xzx/rtl，目录下应有rtl/和eda/。本机需Python 3.8或更新版、Git及OpenSSH的ssh和scp，没有额外pip依赖。SSH测试应直接成功；先完成已有SSH配置或密钥登录，再运行自动流程。Python命令换成你本机可用的解释器即可。

先提交计划部署的代码，可让结果对应一个明确Git提交。打包程序还记录是否有未提交更改及逐文件SHA，但不会代替RTL功能验证。

## 2．一条命令完成压缩、上传、运行和回传

```powershell
python eda/remote.py run
```

总控依次执行下表，任一步失败都会停止并打印原因：

| 动作 | 做什么、为什么 | 生成结果 |
| --- | --- | --- |
| 打包 | 调用package_server.py选出正式服务器程序、RTL和说明，保存提交与逐文件SHA | 本机eda/dist/chip_design_eda.tar.gz及.sha256 |
| 新建上传目录 | 以时间和提交号新建uploads下目录；同名目录已存在就拒绝复用 | 独立uploads/时间_提交/ |
| 上传和解压 | 安装公共unpack.sh，上传包和校验文件，调用解压器核对并解压 | 本版本deploy、配置、阶段脚本和README |
| 检查环境 | 调用check_env.sh准备输入快照，检查工具、PDK、SRAM和显示环境 | doctor.json与environment.log |
| 执行EDA | 调用run_eda.sh完成综合和01–34步，保存命令、报告及检查点 | 逐步运行报告及最终导出 |
| 整理结果 | 调用collect_results.sh生成报告、交付清单和小型回传包 | review_delivery.tar.gz及.sha256、review_manifest.json |
| 回传查看 | 等待完成，下载小包，校验整包、逐文件SHA、34步输入身份和压缩网表，自动解压 | 本机结果目录、receipt.json、README.html |

SHA-256是文件内容的校验值，用于发现传输损坏或内容变化，不证明硬件功能正确。正式服务器脚本原件都在server/entry/，复杂命令已封装，不需要另找临时工具。

服务器任务由nohup启动，关闭本机等待窗口不会停止服务器计算。总控默认每30秒显示阶段和进度，完成后打印本机结果目录；默认在eda/dist/results/版本_时间/。大型物理视图和数据库不会回传。

需要将核心文件直接保存到lab4下时，用一个新的空目录：

```powershell
python eda/remote.py run --output 'C:\Users\zixiang\OneDrive\Desktop\advanced_chip_study\lab4\my_soc_本次版本'
```

## 3．先启动，稍后抓取

```powershell
python eda/remote.py run --detach
python eda/remote.py status
python eda/remote.py fetch --wait
```

run --detach上传并启动三阶段后返回；status只读状态；fetch --wait等待整理结束后回传。本机eda/dist/last_upload.json保存最后上传位置，eda/dist/uploads/保存各次记录；服务器没有全局当前版本指针。

多版本时明确指定--upload，避免选错：

```powershell
python eda/remote.py status --upload '/home/s2400011041/Desktop/fullstack_chipdesign/uploads/本次版本'
python eda/remote.py fetch --upload '/home/s2400011041/Desktop/fullstack_chipdesign/uploads/本次版本' --wait --output 'C:\本机\本次结果空目录'
```

本机等待中断后，直接fetch --wait继续等待和回传。服务器已停止且原因已解决时，用resume --upload '完整版本路径'；它续跑指定版本，不替换冻结输入。正在运行的版本不能重复启动。

## 4．需要调整参数时

默认PDK为/lec/pdk/tsmc180，SRAM资料来自/lec/lab4，系统周期20ns，工具CPU数8。先复制正式配置，再通过--config提交：

```powershell
New-Item -ItemType Directory -Force eda/dist
Copy-Item eda/server/config/design.json eda/dist/my_design.json
notepad eda/dist/my_design.json
python eda/remote.py run --config eda/dist/my_design.json
```

总控在首次check_env.sh冻结输入前，将配置复制到本次上传目录configs/design.json。

| 配置项 | 作用 |
| --- | --- |
| pdk_root、macro_source | 实际可读的工艺库与SRAM资料目录 |
| system_period_ns | 时钟周期；20ns对应50MHz，是实现目标 |
| cpus | 单个工具CPU数，服从服务器资源规则 |
| target_utilization | 规划逻辑密度，默认0.5，为布线和修复留空间 |
| core_size_um | null表示按本轮综合面积规划核心 |
| macro_xy_um | SRAM计划坐标，单位μm |
| hold_target_ns、max_repair_iterations | 修复目标和尝试上限，不放宽最终验收标准 |

SDC、IO和实现脚本也是正式输入。当前profile对应77份RTL、六个信号端口和一个主SRAM。更换顶层、端口或硬宏时，先看[实施与适配说明](docs/实施与适配说明.md)，再重新打包到新版本；不要修改已准备work的输入。

## 5．手动分段操作：与自动总控是同一套脚本

### 5.1 Windows压缩并上传

```powershell
python eda/package_server.py
$EdaHome = (ssh -o ClearAllForwardings=yes chipdesign 'printf "%s" "$HOME"').Trim()
$EdaRoot = "$EdaHome/Desktop/fullstack_chipdesign"
$EdaName = (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + (git rev-parse --short HEAD)
$EdaUpload = "$EdaRoot/uploads/$EdaName"
ssh -o ClearAllForwardings=yes chipdesign "mkdir -p '$EdaRoot/uploads' && mkdir '$EdaUpload'"
if ($LASTEXITCODE -ne 0) { throw '新上传目录创建失败' }
scp -o ClearAllForwardings=yes eda/unpack.sh "chipdesign:${EdaRoot}/unpack.sh"
if ($LASTEXITCODE -ne 0) { throw '公共脚本上传失败' }
scp -o ClearAllForwardings=yes eda/dist/chip_design_eda.tar.gz eda/dist/chip_design_eda.tar.gz.sha256 "chipdesign:${EdaUpload}/"
if ($LASTEXITCODE -ne 0) { throw '部署包上传失败' }
Write-Host "本次服务器路径：$EdaUpload"
ssh -t -o ClearAllForwardings=yes chipdesign "cd '$EdaUpload' && exec bash"
```

包中有server/、rtl/、docs/和source.json；没有PDK、授权SRAM原件、历史结果、开发自检和临时工具。公共解压器安装到顶层，原包始终属于此次新建目录。

### 5.2 服务器解压，然后分别执行三个阶段

```bash
pwd
bash ../../unpack.sh "$PWD"
cat configs/design.json
bash ./check_env.sh
bash ./run_eda.sh
bash ./collect_results.sh
```

pwd应为.../uploads/本次版本。check_env.sh准备工程并检查环境；run_eda.sh做实际实现；collect_results.sh只整理已完成结果。每个命令成功后再继续。

若想连续后台执行，以这条命令代替三个阶段命令：

```bash
nohup bash ./run_all.sh > logs/launcher.log 2>&1 < /dev/null &
```

run_all.sh只是三个独立脚本的顺序调度器。日志在logs/pipeline.log，整轮结束后logs/run_exit_code.txt为0表示三阶段均成功。使用tmux时也可以直接bash ./run_all.sh。

### 5.3 返回Windows抓取与解压

将刚才打印的完整服务器路径填入--upload：

```powershell
python eda/remote.py fetch --upload '/home/s2400011041/Desktop/fullstack_chipdesign/uploads/本次版本' --wait
```

手动上传没有本机last_upload.json，因此这里要明确--upload。回传脚本自动下载、校验、解压，最后打印可双击打开的README.html路径。

## 6．从哪里找报告，如何分析

双击本机回传目录README.html，先看core/evidence/运行报告.md。服务器双击本版本README.html；顶层README.html只供选择版本。

| 本机结果位置 | 内容和用途 |
| --- | --- |
| core/evidence/运行报告.md | 综合及01–34每步的目的、实际命令和生成结果 |
| core/evidence/synthesis.json | 映射后的单元数、面积、SRAM及Latch情况 |
| core/evidence/step_33.json | 最终Setup/Hold、DRV、DRC、供电、信号及天线 |
| core/evidence/step_34.json | DEF、SDF、SPEF、GDS的导出对应检查 |
| core/syn/my_soc_top/reports/ | 原始综合面积、时序、QoR和功耗估计 |
| core/pnr/my_soc_top/reports/postFiller/ | 最终时序汇总和详细路径 |
| core/evidence/34_final_layout.gif | 布局图；headless不生成 |
| review_manifest.json | 小包内容及服务器大文件的路径、大小和SHA |
| receipt.json | 本机包、逐文件和34步输入身份校验结果 |

WNS是最差路径时间余量，单位ns；Setup/Hold都应≥0，TNS和违规路径数应为0。DRV是负载、转换时间、扇出等电气约束违规；DRC检查几何规则。判断要结合原报告和第33/34步说明，IO抽象限制如有分类保留，必须明确列出。

summary.gz为压缩文本汇总，all.tarpt.gz为详细路径。服务器用gzip -cd 文件 | less读取，本机可先解压后用编辑器打开。详细读法见[报告分析](docs/报告查找与分析.md)，术语见[基础知识](docs/基础知识.md)，后端动作见[讲义34步对照](docs/讲义34步与文件对照.md)。分支内已完成实测见[结果与分析](results/README.md)。

本流程是单TT、关闭SI的教学实现；不包含独立晶圆厂DRC/LVS、IR/EM/ESD、功能等价或SDF回标仿真。功耗为无实际活动输入的估计。

## 7．文件结构、恢复与清理

```text
本机eda/
  remote.py              本机总控：run、resume、status、fetch
  package_server.py      正式文件选择及打包
  unpack.sh              公共解压器原件
  server/entry/          三个阶段及可选总调度器原件
  server/config/         设计、SDC、IO及阶段说明
  server/syn/、pnr/、tcl/、tools/、bin/   实际EDA程序
  docs/                  操作、基础知识及分析
  results/               已完成实测结果
  dist/                  本机包、上传记录、回传结果；不提交Git

服务器~/Desktop/fullstack_chipdesign/
  unpack.sh、README.html、README.md     公共解压器与版本索引
  uploads/每次新建版本/
    chip_design_eda.tar.gz、.sha256、upload.json
    deploy/、configs/、work/、logs/、results/、docs/
    check_env.sh、run_eda.sh、collect_results.sh、run_all.sh、run_env.sh
    README.html、README.md
  lab4/                  原Lab4内容
  history/               历史有效结果，不参与新输入
```

失败先看对应logs/environment.log、flow.log、collect.log，再看work/evidence的工具原文。修复可访问环境后重新检查，正常进度可resume；需改变冻结输入或存在未解决工具错误时，用run新建版本，不删除错误标记强行推进。

回传校验后，在服务器对应上传目录预览重复交付压缩包清理：

```bash
bash deploy/server/bin/eda.sh clean --work "$PWD/work" --dry-run
```

核对列表后去掉--dry-run执行。清理保留原上传包、清单、日志、报告、中间文件、检查点及最终视图。清理后再次回传前，执行collect_results.sh重新生成小包。
