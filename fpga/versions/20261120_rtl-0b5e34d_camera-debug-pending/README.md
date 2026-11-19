# RAW摄像头演示构建快照：CPU JTAG待恢复

RTL基线`0b5e34d29c3b0ac333461c0edba8197738906e1a`，RTL未修改。目标A7-35T `xc7a35tcsg324-1`，20 MHz，空SRAM启动。常驻CPU固件与模型需随后通过独立CPU JTAG装入；bitstream没有预置演示结果。

## 已验证

- 完成Vivado 2019.1综合、布局布线、布线后静态时序及bitstream生成。
- 最终18141 LUT、15058寄存器、30 DSP、2 BRAM36；Setup WNS +0.758 ns，Hold WHS +0.023 ns，失败端点均0；布线检查通过。
- 时序结论针对现有约束覆盖的路径：内部未约束端点为0；3个输入/3个输出缺少外部I/O延迟约束，尚非外部JTAG接口的完整时序验证。
- DRC 0错误、174警告。报告完整保留；动态DSP OPMODE的逻辑连接审计见[独立记录](../../../report/camera_demo_raw0b_20261120/dsp_warning_audit.json)，没有宣称全部警告无风险。
- 实际FPGA配置成功，目标`1234-tulA/xc7a35t_0`。为排查CPU JTAG曾配置历史已板测bitstream，最后重新恢复本版本；日志见evidence/。

## 尚未验证

CPU TAP在本版本1 MHz/100 kHz和历史版本1 MHz下均返回全0，IR capture为0、dtmcontrol为0。因此未下载常驻固件，100轮算术与12轮工程模型请求均未执行，没有真实摄像头分类准确率或USB吞吐结论。需要确认外部FT232H四根GPIO跳线、共地、复位和时钟；尚未确定哪项造成故障。

完整SoC多轮RTL仿真及软件测试另见[演示记录](../../../report/camera_demo_raw0b_20261120/README.md)。本目录不代表ASIC面积、ASIC SDF后仿或流片签核。`ACTIVE_VERSION`保留历史已板测版本。

## 使用冻结bitstream

从仓库根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File fpga/demo/run_demo.ps1 `
  -Action program -Build fpga/versions/20261120_rtl-0b5e34d_camera-debug-pending/artifacts
```

该操作重新配置FPGA并清空SRAM。CPU JTAG检查通过后，再按演示说明装入常驻固件和模型。开发板当前已恢复本版本。

`VERSION.json`给出来源、资源、状态和bitstream SHA；`SHA256.json`覆盖归档文件（不含索引自身）。`build-inputs/`保存顶层、约束、Clock Wizard配置、构建入口和RTL源哈希，仅供追溯；重新构建请调用仓库`fpga/demo/`入口，归档脚本的相对目录不作为执行入口。最初综合生成检查点，随后用`implement_checkpoint.tcl`完成实现；原始综合及续跑日志保留，未将中断的单线程对照构建当成成功结果。检查点体积较大留在本机`tools/local/camera_demo/bitstream_raw0b/`，其SHA记录在VERSION中。冻结后不覆盖，后续板测另建新版本。
