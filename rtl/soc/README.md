# 最终版 SoC 接入

[my_soc_top.sv](my_soc_top.sv) 集成课程CPU、AXI、Debug、Boot、主SRAM、DMA和NPU；[my_npu_subsystem.sv](my_npu_subsystem.sv) 提供寄存器译码和忙时写保护，直接实例化har_stream_top。

CPU/Debug/DMA共享AXI，CPU与DMA还共享主SRAM；NPU权重bank独立。无版本选择宏，默认即最终W8A4配置。两个项目集成文件的来源与修改在 [manifest](../manifest.json) 中记录；CPU等外围保持校验。修改接口后运行check、unit和双后端soc。
