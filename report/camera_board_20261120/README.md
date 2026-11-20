# RAW多轮交互真实FPGA板测

RTL基线`0b5e34d`，RTL与compiler未改。A7-35T上的既有20MHz布局布线bitstream经真实下载、CPU JTAG装载8KiB固件、逐字回读、boot key提交和运行，完成100轮算术与12轮合成工程模型请求。两组逐项匹配独立整数参考；序号/执行计数分别连续1–100和1–12。每轮不重载权重、不halt CPU。换模型前重新配置空SRAM bitstream。

最终测量绑定相同的host/protocol/transport源SHA，见[evidence/independent_audit_final.json](evidence/independent_audit_final.json)。审计为独立离线逐项核对；物理操作来自父任务的Vivado/OpenOCD执行日志。实际输出JSONL、命令、主机和OpenOCD原日志保存在evidence/，字节与独立审计快照一致。两个最终OpenOCD日志均0条Error/Warn。源码、bitstream、固件、参考输入/输出及资源/时序报告见[冻结版本](../../fpga/versions/20261120_rtl-0b5e34d_live-board-pass/README.md)。

| 项目 | 算术100轮 | 合成工程模型12轮 |
| --- | --- | --- |
| 输入来源 | 四种INT8向量各重复25次 | 12种合成浮点特征，经主机量化 |
| 输出正确数 | 100/100 | 12/12 |
| CPU周期 | 8139–8156 | 8834–8847 |
| 20MHz下接受至结果公布 | 0.40695–0.4078ms | 0.4417–0.44235ms |
| 本次主机往返 | 328–468ms，均值390.85ms | 46–63ms，均值53.5ms |

主机往返含USB/JTAG、Windows/WSL调度，运行时摄像头/CUA并发负载未经控制；不能据此宣称前后性能提升、芯片计算耗时或摄像头FPS。CPU周期不含摄像头和USB。两组均为RAW首层+片上CPU末层，不覆盖旧HAR硬件重标定结果路径。

## 修复和连接

此前线缆/供电调整后，10kHz、100kHz及1MHz均读到ID1和XLEN32，物理SBA、halt/resume也成功。保持开发板USB和外接FT232H同时连接；完整六线和J5方向见[演示说明](../../fpga/demo/README.md)。默认ID的厂家字段0被OpenOCD显示为invalid，不是CPU扫描失败。

首次真实主机装载暴露OpenOCD0.12命令差异：改为仅在新版tcl命令确实不存在时回退到tcl_notifications/tcl_trace。又给所有SRAM/MMIO内存读写显式添加phys，绕过运行中hart的虚实地址/PRIV探测，仍强制sysbus并保留真实总线错误。17项主机测试通过。修复后重新做了两次完整装载及112轮实测，最终无上述诊断；并非屏蔽错误日志。

## 真人摄像头状态

真人数据尚未采集成功。首次用户做动作但未逐项按SPACE，未保存任何样本；重开后曾停在首项等待，之后因没有有效全身64维特征而退出1（No valid 64-dimensional feature samples to save），未保存样本；取景需调整到全身。用户随后明确选择自动倒计时切换动作，自动采集代码及16项摄像头测试已完成：全身姿态门控、自动倒计时与切换、无效样本重试、中文界面；本次尚未重新启动或做真人自动采集。Computer Use收到用户物理Escape停止信号后，停止所有界面操控，不自动重开摄像头。未上传用户照片、视频或姿态数据。本记录不把合成工程模型的正确输出当真人识别准确率。

后续为六类各至少三个独立session采样、按session划分训练/验证/测试、量化并检查真人模型在FPGA上的整数一致性，再启动实时显示。当前物理数值链路已通过，真人端到端演示仍待完成。

旧[构建记录](../camera_demo_raw0b_20261120/README.md)及[接线失败记录](../jtag_photo_recheck_20261120/README.md)保持原样作为历史快照，不覆盖。SHA256.json覆盖本记录文件（不含索引自身）。

自动采集入口：`powershell -NoProfile -ExecutionPolicy Bypass -File fpga/demo/run_demo.ps1 -Action collect`。直接CLI可用`camera collect --auto-advance --countdown 10 --pose-timeout 120`；详见演示说明。
