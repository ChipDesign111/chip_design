# FPGA：从新机器准备到板测

仓库保存板级源码、配置、执行脚本和[测试报告](results/README.md)。Vivado 工程、IP、固件、bitstream、日志和测试输出全部放在仓库外。默认工作区是仓库的同级目录 `../fpga_workspace`；可用环境变量 `FPGA_WORKSPACE` 或每条命令的 `--workspace` 指定其他外部目录。脚本拒绝将生成目录设在仓库内。

板卡为 A7-35T，器件 `xc7a35tcsg324-1`，输入时钟 100 MHz，SoC 时钟 20 MHz。配置入口为 [board.json](config/board.json)，引脚约束见 [fpga_top.xdc](src/fpga_top.xdc)，板级连接见 [fpga_top.sv](src/fpga_top.sv)。本次仅迁移板级文件位置，没有修改硬件逻辑。

## 1. 新机器准备

需要 Git、Python 3.10+、Vivado（本流程已用 2019.1 创建工程验证）。生成 RAW 配对包还需[编译器依赖](../compiler/requirements.txt)中的 PyTorch/NumPy；批量板测只使用 Python 标准库。

从仓库根目录在 PowerShell 执行，以下路径均为可替换的示例：

~~~powershell
$env:FPGA_WORKSPACE = [IO.Path]::GetFullPath('../fpga_workspace')
$env:VIVADO = 'D:/Xilinx/Vivado/2019.1/bin/vivado.bat'
python -m venv "$env:FPGA_WORKSPACE/python"
& "$env:FPGA_WORKSPACE/python/Scripts/python.exe" -m pip install -r compiler/requirements.txt
python fpga/run.py doctor
python fpga/run.py prepare --compiler-python "$env:FPGA_WORKSPACE/python/Scripts/python.exe"
~~~

Linux 的虚拟环境解释器位于 `python/bin/python`，Vivado 使用安装目录下的 `bin/vivado`。也可先加载 Vivado 的 `settings64.sh`，通过 PATH 查找。`--vivado` 可代替 `VIVADO`。已有 PyTorch 环境时直接传给 `--compiler-python`。

`prepare` 重新生成并验证全部固件，创建外部 GDB 入口，并在不存在时复制 OpenOCD 配置；不会覆盖已经调整过的外部 `config/cv32e40p.cfg`。

~~~text
仓库/
  rtl/                     SoC 与 NPU RTL
  fpga/src/                板级顶层与引脚约束
  fpga/config/             器件、时钟与 OpenOCD 默认配置
  fpga/tcl/                可重建 Vivado 工程的流程
  fpga/firmware/           固件生成器、验证器源码
  fpga/results/            筛选后的测试报告
fpga_workspace/            全部本机生成物
  final_project/           final_project.xpr、IP、runs、bitstream
  firmware/                38 个 HAR 镜像及 suite/ 下 24 个配对包
  gdb/                     手动装载与一键批测入口
  config/                  生成的工程配置、本机 OpenOCD 配置
  logs/                    prepare / Vivado 日志及输入 SHA
  tests/                   板测和脚本检查结果
  presim/                  可选的完整 SoC 仿真输出
  archives/                本机迁来的历史完整归档（新机器无需具备）
~~~

脚本以当前检出的源码为输入。切换提交后先重新 `prepare`，再 `build`；新机器无需复制旧 `.xpr/.xci` 或固件。

## 2. 创建和构建外部工程

~~~powershell
# 只创建/打开工程并准备时钟 IP，不运行综合实现
python fpga/run.py project

# 默认：无预装固件，综合、实现并生成 bitstream
python fpga/run.py build --jobs 4

# 打开外部工程，Vivado 运行目录也在工作区
python fpga/run.py gui
~~~

`project` 从 [rtl/filelist.f](../rtl/filelist.f) 收集源码并创建 Clock Wizard 6.0。`build` 重置所选 run 后重新构建，日志与输入 SHA 保存在外部 `logs/`。只综合可用 `build --stage synth`。

| 模式 | 命令 | runs | SRAM 初值与启动 |
|---|---|---|---|
| JTAG 装载 | `build --mode runtime`（默认） | `synth_2 → impl_2` | 空初值，完整装载并提交后启动 |
| 预装自检 | `build --mode preload` | `synth_1 → impl_1` | 外部 `firmware/int8_selftest.hex`，上电自动启动 |

日常切换固件使用 runtime。bitstream 位于外部 `final_project/final_project.runs/impl_2/fpga_top.bit`。预装模式每次修改镜像都要重新构建。

runtime 的综合参数应为 `-generic SRAM_INIT_FILE=`。Vivado 2019.1 的 More Options 中不要填 `SRAM_INIT_FILE=""`，它会把双引号当作实际字符。综合日志应显示 `SRAM_INIT_FILE bound to: 0` 和 `PREINITIALIZED bound to: 1'b0`。

在 Vivado Hardware Manager 的 Tcl 控制台中加载仓库脚本，再传入外部 bitstream 路径：

~~~tcl
source /path/to/repository/fpga/connect_fpga.tcl
har_program_fpga /path/to/fpga_workspace/final_project/final_project.runs/impl_2/fpga_top.bit
~~~

脚本动态查找在线 `xc7a35t`，无需保存另一台机器的 JTAG 序列号。`vivado_init.tcl` 也可从任意仓库位置加载。烧写后关闭 Hardware Manager，再交给 OpenOCD。

## 3. WSL/Linux 的 OpenOCD

需要支持 RISC-V Debug 的 OpenOCD 和 RV32 GDB。本机验证过的 OpenOCD 是 `riscv-openocd` 提交 `10b7a647d`（版本字符串 `0.12.0+dev-04406-g10b7a647d`）；RISC-V GDB 来自 xPack GCC 13.2.0-2。GDB 无需内置 Python。

外接 JTAG 使用 FT232H `0403:6014`。接线为 ADBUS0/TCK→E15、ADBUS1/TDI→E16、ADBUS2/TDO←D15、ADBUS3/TMS→C15，并共地。`0403:6010` 为另一 USB 串口设备。实际总线号用 `usbipd list` 查询，管理员 PowerShell 例：

~~~powershell
usbipd list
usbipd bind --busid 2-2
usbipd attach --wsl --busid 2-2
~~~

在 WSL 设置与 Windows 相同位置的工作区，使用 `/mnt/d/...` 路径，然后：

~~~bash
export FPGA_WORKSPACE=/path/to/fpga_workspace
sudo openocd -f "$FPGA_WORKSPACE/config/cv32e40p.cfg"
~~~

默认适配器频率 10 kHz，GDB/Tcl 端口为 3333/6666。端口占用时先确认是否已有自己的 OpenOCD 在运行。默认配置源码见 [cv32e40p.cfg](config/cv32e40p.cfg)。

当前 Boot ROM 会等待 `ready` 后才跳 SRAM，DM 正确报告 unavailable。实现原理与验证见[启动与调试修复](../report/boot_debug_guard.md)；必须烧写包含这些 RTL 的 bitstream，单独更换固件不会更新硬件。

## 4. 手动装载和检查

在 WSL 启动 `riscv-none-elf-gdb`，以下路径替换为外部工作区：

~~~gdb
target extended-remote :3333
cd /path/to/fpga_workspace
source gdb/load_soc_image.gdb
monitor reset halt
maintenance flush register-cache
soc-boot-status
soc-load-bin firmware/suite/raw_full_b4_raw/firmware.bin
soc-commit-image
monitor resume 0x00010000
shell sleep 1
monitor halt
maintenance flush register-cache
source firmware/suite/raw_full_b4_raw/check.gdb
soc-check-result
soc-full-cycles
soc-npu-counters
~~~

换固件时从 `monitor reset halt` 重做，换成对应 `.bin` 和 `check.gdb`。显式从 `0x00010000` 启动，保证新镜像从入口执行；按键复位不会清 SRAM，也不保证调试器保存的 DPC 指向入口。重新 source 检查脚本时的 `Redefine command` 是正常替换。

| 时点 | `soc-boot-status` |
|---|---|
| runtime 复位后 | `loaded_words=0 ready=0`，状态 `0x00000000` |
| 完整写入 8 KiB | `loaded_words=2048 ready=0`，状态 `0x00000800` |
| 提交 `0xB007C0DE` 后 | `loaded_words=2048 ready=1`，状态 `0x00002800` |

部分装载或错误提交码不能启动。`soc-load-bin` 顺序重写全部 2048 个字。固件完成后停在自己的自循环，读寄存器和内存前先 halt；GDB 使用 `maintenance flush register-cache` 刷新 PC。

RAW 的 PASS 标志和 LED 只说明执行完成，数值正确须以 `soc-check-result` 为准。加速比使用同组 `CPU full_soc_cycles / 硬件 full_soc_cycles`，排除 JTAG 装载和等待时间。NPU cycles、FC1/FC2、DMA/MAC read/write/total overlap 仅代表最后一个任务；`total` 是重叠周期并集。

## 5. 一键批测和保存报告

在已连接的 WSL GDB 中 source 外部自动生成的入口：

~~~gdb
source /path/to/fpga_workspace/gdb/test_all_firmware.gdb
~~~

它会断开 GDB，使用现有 OpenOCD 依次测 62 份固件，再重新连接。输出在外部 `tests/fpga_board_时间戳/`，包括完整周期、DMA/MAC overlap 和 12 组加速比。筛选和失败处理见[批量板测](FIRMWARE_BATCH.md)。

从 WSL 仓库根目录也可运行；先在 GDB 中 `disconnect`：

~~~bash
python3 fpga/run.py test
python3 fpga/run.py test --only 'raw_full_b4_*'
~~~

确认一份实际测试输出后，从仓库根目录收录轻量报告：

~~~bash
python3 fpga/run.py collect --run /path/to/fpga_workspace/tests/fpga_board_TIMESTAMP --name board_YYYYMMDD
~~~

`collect` 只复制 `result.json`、`summary.md/csv`、`speedups.csv` 和校验收据到 `fpga/results/` 的新目录，保留测试环境与结论；不会收录固件、工程、bitstream 或逐命令原始日志，不覆盖已有报告。构建和上板并不会自动修改仓库报告。

## 6. 离线验证

~~~powershell
python fpga/run.py validate
python test/int8/test_fpga_workspace.py
python test/int8/test_firmware_batch.py
# 可选：重新跑所有实际固件的 SoC 仿真，输出在外部 presim/
python fpga/run.py validate --simulate --vsim D:/modeltech64_2019.2/win64/vsim.exe
~~~

批测脚本测试需要先 `prepare`，只连接临时本机 TCP fixture。当前已保留的板测、前仿与迁移验证范围见 [TEST_REPORT.md](TEST_REPORT.md)；历史报告不能替代当前 RTL 的新构建或板测。
