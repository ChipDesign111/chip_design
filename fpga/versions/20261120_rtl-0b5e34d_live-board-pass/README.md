# RAW多轮数值板测通过快照

基线0b5e34d，RTL与compiler未改。复用20261120构建的20MHz空SRAM bitstream（SHA ce118945509b83d281c657aa8297aab0afcdb7eb6fb9b78332b380f2bc0e6efa），没有重新综合或声称新的ASIC签核。

已真实配置A7-35T，CPU JTAG ID1/XLEN32，最终主机源码下完整装载并回读两个8KiB镜像，执行100轮算术+12轮合成工程模型请求，全部返回正确张量和类别；最终OpenOCD日志0Error/Warn。详见[板测报告](../../../report/camera_board_20261120/README.md)与evidence/。host/保存测量源码，firmware/保存两个模型包及参考数据；build-inputs/和reports/复用原物理构建追溯文件，重新构建调用仓库fpga/demo入口。

最终18141LUT、15058FF、30DSP、2BRAM36；Setup WNS+0.758ns、Hold WHS+0.023ns，内部失败端点0。DRC0错误、174警告；3输入/3输出缺外部I/O delay约束，不代表完整外部接口签核。保留原[DSP审计](../../../report/camera_demo_raw0b_20261120/dsp_warning_audit.json)及全部报告。

真人采样尚未成功，真实动作准确率/实时演示仍待完成。工程模型的12种合成特征不是真人动作数据。CPU周期和USB往返分别记录，不能将两组不同并发负载下的往返时间当受控优化结论。未修改历史冻结版本。

从仓库根目录可用：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File fpga/demo/run_demo.ps1 -Action program -Build fpga/versions/20261120_rtl-0b5e34d_live-board-pass/artifacts
```

配置后需启动OpenOCD，再用fpga.demo.host装载本目录firmware/arithmetic或firmware/engineering。换模型先重新配置空SRAMbitstream；该bitstream没有预存推理结果，也未写入板载SPI Flash。

VERSION.json给出来源/状态/测量绑定，SHA256.json覆盖全部归档文件（不含索引自身）。后续改动另建版本，不覆盖本快照。
