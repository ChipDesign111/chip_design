# 摄像头 → FPGA 多轮动作演示（RAW 备选版）

本演示按用户指定的备选基线 `0b5e34d29c3b0ac333461c0edba8197738906e1a` 开发。PC 用摄像头和 MediaPipe 提取姿态，FPGA 上的真实 CPU/NPU 执行 64→32→6 INT8 分类器，PC 读回结果并显示。姿态提取在 PC，动作分类在 FPGA；不是将整张图像或 MediaPipe 网络放进 8 KiB SRAM。

```mermaid
flowchart LR
    A[电脑摄像头] --> B[PC姿态检测与64维时间窗特征]
    B --> C[JTAG / Debug SBA]
    C --> D[SRAM请求邮箱]
    D --> E[常驻CPU程序]
    E --> F[RAW NPU / 16 MAC / 双bank]
    F --> G[结果张量与完成编号]
    G --> C
    C --> H[PC实时显示类别与延迟]
```

RAW完整SoC多轮仿真和真实FPGA数值回传均已通过：最终主机源码下100轮算术请求、12轮合成工程模型请求逐项匹配独立整数参考，换模型后重新装载8KiB镜像；另有同模型attach续跑验证。CPU JTAG在1MHz读到ID `0x00000001`、XLEN32。主机17项测试通过，实际读写使用物理地址SBA。最新证据见[真实板测记录](../../report/camera_board_20261120/README.md)，早期构建/RTL记录见[基线记录](../../report/camera_demo_raw0b_20261120/README.md)。真人动作数据与识别精度须单独采集验证；原UCI HAR传感器模型不能沿用到摄像头坐标。

## 软件与环境

Windows PowerShell，在仓库根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File fpga/demo/setup.ps1
.\.venv-demo\Scripts\python.exe -m fpga.demo.doctor
```

依赖安装在 `.venv-demo`，姿态前端下载到忽略目录 `tools/local/camera_demo`。官方模型 URL 和 SHA 固定在 [assets.py](assets.py)，它只用于 PC 姿态检测；FPGA 动作模型由自己的摄像头样本训练。未下载视频和真人数据。

还需 Vivado（本机已找到 `D:/pkuwyh/Vivado/2019.1/bin/vivado.bat`）及 OpenOCD。本机 WSL Ubuntu 已安装 OpenOCD 0.12、usbutils，Windows 已安装 usbipd-win。安装依据：[微软 WSL USB 文档](https://learn.microsoft.com/en-us/windows/wsl/connect-usb)、[OpenOCD Tcl RPC](https://openocd.org/doc/html/Tcl-Scripting-API.html)。

## FPGA 配置与连接

目标器件为 `xc7a35tcsg324-1`，板载100MHz经Clock Wizard产生20MHz。[已板测RAW快照](../versions/20261120_rtl-0b5e34d_live-board-pass/README.md)复用先前通过布局布线的同一bitstream，SHA未变；没有因为主机兼容修复重新修改RTL或声明新的ASIC结果。以下命令供重新构建使用。

```powershell
& 'D:\pkuwyh\Vivado\2019.1\bin\vivado.bat' -mode batch -nojournal `
  -source fpga/demo/build_bitstream.tcl `
  -tclargs tools/local/camera_demo/bitstream_new
& 'D:\pkuwyh\Vivado\2019.1\bin\vivado.bat' -mode batch -nojournal `
  -source fpga/demo/program_bitstream.tcl `
  -tclargs tools/local/camera_demo/bitstream_new/fpga_top.bit
```

构建输出目录必须新建；只在资源、布线和时序通过后生成成功状态。空 SRAM bitstream 先配置 FPGA，模型与常驻程序再通过 JTAG 装载一次。运行不需要每轮重新烧录 FPGA，也不需要每轮重载权重。

板载配置链和 SoC 的 JTAG Debug 引脚是两条不同通路。现有顶层把 TCK/TMS/TDI/TDO 放在 E15/C15/E16/D15，沿用课程接线；下载链能看到 `xc7a35t`，不代表 OpenOCD 已能访问内部 CPU。独立 FT232H 适配器通常为 `0403:6014`，板载复合设备为 `0403:6010`。不应将后者的 FPGA 配置 TAP 当成 RISC-V DTM。以实际接线和 TAP 探测结果为准。

本机照片已确认板卡为EGo1，下载器外观与课程ALINX USB CABLE一致。按[课程Lab6第8.2节](https://full-stack-ai-chip.tianyuj.com/lab-6/#82-jtag)和[EGo1手册第14节](https://e-elements.readthedocs.io/zh/ego1_v2.2/EGo1.html)核对完整六线连接：

| 下载器信号 / FT232H | EGo1 J5针号 | FPGA封装引脚 / 方向 |
| --- | --- | --- |
| TCK / AD0 | 17 | E15，适配器输出 |
| TDI / AD1 | 18 | E16，适配器输出 |
| TDO / AD2 | 19 | D15，适配器输入 |
| TMS / AD3 | 20 | C15，适配器输出 |
| GND | 33或34 | 共地 |
| VREF | 35或36 | +3.3V，下载器参考电压输入 |

此前五线说明遗漏了该款下载器的VREF，已更正；不能只按裸FT232H的四根GPIO加GND描述外接成品下载器。VREF用于目标电平参考，不用于给开发板供电，也不能接5V。

课程图针对下载器端面2×5插口：标签面朝上、正对该插口看，上排从左到右为`TDI / 空 / TMS / TDO / TCK`，下排为`GND / 空 / 空 / VREF / GND`。这一顺序不适用于外壳顶部的长窗口插针。J5为2×18排针。本机EGo1已通过背面首针方形焊盘核实：正面朝向自己、VGA在上时，最上方左=1、右=2；左列奇数、右列偶数，向下递增。第9对17/18、第10对19/20；倒数第二对33/34为GND，最后一对35/36为3.3V。正反面左右相反；不同板卡应自行核实首针标记。

E15等是FPGA封装脚号，不是排针号。两根USB都需连接：板载USB负责供电/配置，外接适配器负责CPU调试。VREF不能替代开发板供电。若开发板断电，需先重新配置bitstream再装模型。早期全0/全1诊断保存在[照片与接线复核](../../report/jtag_photo_recheck_20261120/README.md)；接线调整并恢复板载USB后，10kHz、100kHz及1MHz均成功识别CPU，最终数值板测通过。TAP复位仍受外部复位和MMCM锁定控制。

启动已安装的WSL并附加外接适配器后，在仓库根目录启动OpenOCD：

```powershell
wsl -e openocd -f /mnt/c/Users/wyh/Desktop/chipcourse/chip_design_demo_raw0b/fpga/demo/openocd_ft232h.cfg
```

成功标志包括`tap/device found: 0x00000001`、`Examined RISC-V core`和`XLEN=32`；端口监听本身不代表连接成功。若仍含`all zeroes`、`all ones`、`IR capture error`或`dtmcontrol is 0`，应先恢复CPU调试链，再装固件。RTL默认ID的厂家字段为0，OpenOCD会显示厂家`<invalid>`；不能将它和扫描失败混淆。

WSL使用USB/IP时，先在Windows执行`usbipd list`核对适配器BUSID；管理员执行一次`usbipd bind --busid BUSID`，再`usbipd attach --wsl --busid BUSID`。只将外接FT232H附加WSL，板载下载口留给Vivado。Tcl RPC端口为6666。主机强制`sysbus`并给SRAM/MMIO读写显式加`phys`，避免运行中hart的虚实地址探测；每轮不halt CPU。OpenOCD0.12使用`tcl_notifications`/`tcl_trace`，新版命令不存在时才回退，实际错误继续报告。

## 采集与训练动作

默认六类是站立、左臂抬起、右臂抬起、双臂抬起、下蹲、侧倾；它们是演示标签，尚无已验证真人分类器。可以用 `--labels` 提供六个其他标签，但训练、采集、显示必须使用同一份标签顺序。

采集时需全身入镜，包括肩、髋、膝和脚踝；只有上半身时不会保存有效窗口。推荐自动模式：检测到连续有效全身姿态后，先显示当前中文动作并倒计时10秒，再录制10秒，自动切换下一个动作，无需逐项按SPACE。准备期间丢失全身会重新等待；录制期间仅保存有效窗口，样本不足则留在同一动作重试，不把空段当完成。默认每动作总期限120秒，超时退出并保留此前完成的session。

```powershell
.\.venv-demo\Scripts\python.exe -m fpga.demo.camera collect `
  --auto-advance --countdown 10 --pose-timeout 120 `
  --output tools/local/camera_demo/actions.npz
.\.venv-demo\Scripts\python.exe -m fpga.demo.train_camera `
  --dataset tools/local/camera_demo/actions.npz `
  --out tools/local/camera_demo/my_action_model
```

引导采集分三轮、每轮六类。默认动作依次为站立、左臂、右臂、双臂、下蹲、侧倾；自动模式在达到有效样本门槛后才切换。Q退出，自动模式不保存当前未完成段，已完成session保留。省略`--auto-advance`仍可手动逐项按SPACE开始。`run_demo.ps1 -Action collect`默认自动模式，`-ManualCapture`恢复手动。中文界面使用本机微软雅黑/Pillow，无中文字体时显示英文，不下载字体。

保存的是64维特征、标签和独立session标识，不保存原视频。每类至少三次独立session，训练/验证/测试按session划分，避免相邻重叠帧随机切分造成精度虚高。若检验不同人的泛化，需另外采集不同人的独立测试session。自动模式的16项摄像头代码测试已通过，真实自动采集仍需用户全身入镜完成；代码测试不等于已获得样本。

特征契约为 16 个身体关键点的归一化二维位置 32 维，加约 1 秒窗口的位移 32 维。坐标以髋中心平移、躯干尺度归一化；具体关键点、缺失检测和窗口规则见 [features.py](features.py)。采集与推理共用同一实现和特征版本。丢失姿态时不发送伪造的零输入。

训练工具生成浮点权重、定点校准、`compiled/` 原始任务包以及 `resident/` 常驻程序包。第一层完整 32×64 块使用 RAW NPU，重标定及第二层 32→6 边缘计算由 FPGA 内的 CPU 完成；逐层后端与 RAW 工作量写入 metadata。至少必须有真实 RAW NPU 工作，否则拒绝作为此演示模型。测试集精度和浮点/量化分类一致性会单独记录。合成样本仅可用于流程测试，不能代替真人精度。

## 连续推理

配置 FPGA、启动 OpenOCD，随后执行：

```powershell
.\.venv-demo\Scripts\python.exe -m fpga.demo.camera run `
  --package tools/local/camera_demo/my_action_model/resident
```

启动时装载 8192 字节镜像、逐字回读、提交 boot key，CPU 开始等待请求。已装载相同模型且处于空闲状态时可加 `--attach`。更换模型需要复位并重新装载；模型标签和 FPGA 程序 tag 必须匹配。界面只把 FPGA 返回的结果显示为 FPGA 结果，连接错误、超时、过期结果会明确显示。单个后台推理线程最多保留一份最新待处理特征，避免 USB 较慢时无限排队。

不用摄像头也可先检验多轮数值回传：

```powershell
.\.venv-demo\Scripts\python.exe -m fpga.demo.host PATH_TO_RESIDENT `
  --inputs inputs.json --int8 --expected expected.json `
  --output tools/local/camera_demo/board_results.jsonl
```

`inputs.json` 是二维列表，每行一组新输入；`--int8` 表示有符号 INT8，省略则按模型 input_scale 量化浮点特征。`expected.json` 是独立整数参考输出，只供 PC 核对，不会作为 FPGA 输出写入芯片。

## 请求/结果协议

邮箱占 SRAM 顶端 64 B，基址 `0x80001fc0`，实际输入输出地址由 `manifest.json/live_demo` 给出。只有一个未完成请求：host 先写输入和命令，最后写非零 `request_seq`；CPU 先写完整结果、状态、错误和计时，最后写 `response_seq`。host 只接受编号匹配且状态 DONE 的结果，重复编号不重跑；超时保留该 slot，可等待原请求恢复，不能覆盖仍在计算的输入。

| 偏移 | 字段 | 写入方 |
| --- | --- | --- |
| 0 / 4 | LIVE magic / ABI version | 固件 |
| 8 / 12 | request_seq / response_seq | PC / CPU |
| 16 / 20 | command / input_bytes | PC |
| 24 / 28 | status / error | CPU |
| 32 / 36 / 40 | cycles / executions / argmax | CPU |
| 44 / 48 / 52 | output_bytes / input_address / output_address | 固件 |
| 56 / 60 | model/program tag 低字 / 高字 | 固件 |

常驻 CPU 程序每轮装入新输入，调度 RAW NPU 和 CPU 内核重新计算激活并写回输出。权重与量化参数固定在模型包，输入和中间激活不再固定为启动镜像的测试值。完整 ABI 在 [protocol.py](protocol.py)，生成入口在 [firmware.py](firmware.py)。输出为编译器的 INT8 分数，不是概率。

`cycles` 记录 CPU 接受请求至结果公布，不包含摄像头、特征时间窗、USB/JTAG 搬运和主机显示。界面另显示电脑端往返延迟，不能把功能仿真时钟或周期数当成实际摄像头 FPS。

常驻程序持续等待下一轮，不写旧自检的 PASS 标记；心跳灯继续闪烁属于正常现象。是否成功以请求编号、返回状态和结果比对为准。

## 开发验证

```powershell
.\.venv-demo\Scripts\python.exe -m unittest discover -s test/int8 -p 'test_camera_demo.py' -v
.\.venv-demo\Scripts\python.exe -m unittest discover -s test/unit -p 'test_live_host.py' -v
python tools/project.py check
```

完整 SoC 多轮测试入口是 [run_live_demo.py](../../test/int8/run_live_demo.py)，需要 Xcelium。该 bench 经 Debug SBA/AXI 边界在 CPU 运行时送数据，覆盖多轮、重复请求、错误参数和恢复；它没有模拟 USB 物理设备或完整串行 JTAG 电气链。主机 fake transport 测试也不作为板测证据。

本机 RAW 工作目录通过 `.venv-demo` junction 复用同工作区的已安装环境；新电脑运行 setup 会创建独立环境。本版本保持原始 RAW RTL 及其默认四样本能力，没有使用任务引擎分支的单样本 RTL 改动。

真人 camera run 默认拒绝 synthetic/未知来源模型。`--allow-synthetic-engineering-test` 仅供明确的工程检查，并在界面持续显示工程测试标记，不能据此宣称识别准确率。
