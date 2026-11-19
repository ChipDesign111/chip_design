# RAW 基线摄像头多轮演示

用户指定 `0b5e34d29c3b0ac333461c0edba8197738906e1a` 作为资源超限时的备选。工作分支 `codex/camera-fpga-demo-raw-20261120`，目录 `chip_design_demo_raw0b`。前一个任务引擎基线完整配置综合为 22433 LUT，超过 A7-35T 的 20800；按用户指示切到此 RAW 基线。任务引擎版本的开发代码与证据独立保留。

本版本复用原始 RAW RTL，不修改 ASIC 硬件。新增常驻 CPU 固件、多轮 SRAM 请求/结果协议、OpenOCD JTAG 主机、摄像头特征采集及本地训练。模型64→32→6：首层完整块由NPU执行，末层小矩阵由FPGA内CPU执行，PC负责MediaPipe姿态前端和显示。

完整 SoC 多轮仿真已通过：四轮新输入、4 次 RAW 启动、128 次隐藏层写入，每轮隐藏层及最终输出/argmax与独立整数参考一致；重复请求、错误参数恢复和编号环绕均通过。合法请求为9043/9037/9028/9024拍，计时不含USB。原始日志和全部源文件SHA见 [soc/](soc/)。该测试经SBA/AXI边界注入事务，尚非实际USB/JTAG线级测试。

FPGA 综合、布局布线和 20 MHz 布线后静态时序已通过，并已实际下载到 `xc7a35t_0`。综合占18220/20800 LUT（87.60%）；最终布线后18141 LUT、15058寄存器、30 DSP、2 BRAM36，Setup WNS +0.758 ns、Hold WHS +0.023 ns、两类失败端点均为0。该结论针对现有约束覆盖的路径；内部无未约束端点，但3个输入/3个输出缺少外部I/O延迟约束，不能据此宣称外部JTAG接口时序已完整验证。布线检查通过，DRC为0错误、174警告；DSP警告的具体连接审计见 [dsp_warning_audit.json](dsp_warning_audit.json)，不将全部警告统称为无害。DSP为全SoC用量，不等于NPU MAC数量；NPU保留16 MAC。冻结bitstream、构建报告、三次配置和JTAG诊断日志见 [FPGA版本归档](../../fpga/versions/20261120_rtl-0b5e34d_camera-debug-pending/README.md)，汇总见 [fpga_result.json](fpga_result.json)。这些是FPGA资源与时序结果，不能换算为2×2 mm ASIC面积，也不是新一轮ASIC后仿或签核。

**物理推理尚未通过。** 外接FT232H已被USB/IP和OpenOCD识别，但CPU JTAG TAP返回全0：新RAW bitstream在1 MHz、100 kHz均失败，历史已板测bitstream在1 MHz也失败，均为IR capture 0 / dtmcontrol 0。三次FPGA配置都成功，最后已恢复新的RAW bitstream。问题范围仍包括外部GPIO接线、共地、复位或时钟，尚不能确定具体原因；没有加载常驻固件，100轮算术回传和12轮工程模型回传均为NOT_RUN。打开OpenOCD端口不代表CPU已连接。需要用户醒来后确认四根JTAG跳线及共地，接线见演示说明；随后才执行真实数值回传。

操作入口见 [摄像头演示说明](../../fpga/demo/README.md)。真人带标签采样仍需用户执行引导动作；仅保存特征、不保存原视频。工程测试使用合成特征，准确率不能作为真人泛化指标。

摄像头链路11项单元测试及官方姿态模型黑帧API检查通过；288个合成工程样本/18个独立session完成训练、量化和RAW打包。合成包默认不能用于真人camera run，只有显式工程测试选项才允许并显示标记。详情见camera_tests.json。

主机13项测试通过，覆盖请求发布顺序、过期结果拒绝、超时恢复，以及原生socket在阻塞读取时关闭连接；这是fake/TCP测试，不是板测。见 [host_tests.json](host_tests.json) 和 [host_unit_test.txt](host_unit_test.txt)。

## 接线恢复后的复测

[prepared_but_not_run/](prepared_but_not_run/) 保存待执行向量及工程模型包，不含板上运行结果。先用空SRAM bitstream启动并确认OpenOCD能检查CPU；再从仓库根目录运行100轮算术比对：

```powershell
.\.venv-demo\Scripts\python.exe -m fpga.demo.host report/camera_demo_raw0b_20261120/soc `
  --inputs report/camera_demo_raw0b_20261120/prepared_but_not_run/arithmetic/inputs.json `
  --int8 --expected report/camera_demo_raw0b_20261120/prepared_but_not_run/arithmetic/expected.json `
  --timeout 30 --output tools/local/camera_demo/board/results.jsonl
```

100轮由四种向量重复25次组成，检查多轮交互稳定性，不等于100种独立模型场景。完成后重新配置空SRAM bitstream，再装另一个模型，运行12轮浮点特征的量化与回传：

```powershell
.\.venv-demo\Scripts\python.exe -m fpga.demo.host report/camera_demo_raw0b_20261120/prepared_but_not_run/camera/resident `
  --inputs report/camera_demo_raw0b_20261120/prepared_but_not_run/camera/inputs_float.json `
  --expected report/camera_demo_raw0b_20261120/prepared_but_not_run/camera/expected_int8.json `
  --timeout 30 --output tools/local/camera_demo/board_camera/results.jsonl
```

第二组为合成特征训练出的工程模型，只用于软件/硬件整数一致性；真人识别需按摄像头说明采集带标签动作、训练自己的模型，再测试。两组均使用RAW FC1及CPU末层，不覆盖旧HAR硬件重标定结果路径。

SHA256.json覆盖本记录全部文件（不含索引自身）。`state.json`区分构建、配置、物理推理与真人数据状态。
