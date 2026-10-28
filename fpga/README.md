# 从 main 保留的 Vivado 工程

本分支主要验证服务器 TSMC180 ASIC 流程。保留 main 更新的 Vivado 2019.1 工程、A7-35T 引脚和时钟生成配置；当前 filelist 及 firmware/int8_selftest.hex 已适配 INT8 tile DMA。默认综合在 A7-35T 上仍超出 LUT 容量，因此综合使用 `Flow_AreaOptimized_high`，implementation 保持 Default。若后续 RTL 已降到容量内，应优先重新评估 Default，而不是长期保留高面积优化。

使用 configure_final_project.tcl 重新生成源清单；该脚本会把固件绝对路径写入 synthesis generic，再构建。旧并行架构在 main 的 LUT 超限结论属于旧实现；本分支没有重新宣称板上运行或 Vivado 面积已验证。固件从 test/int8/firmware.py 生成，CPU 通过 MMIO 做训练模型两个样本自检。

2026-10-29 实测：AreaOptimized_high 综合为 15938 个 Slice LUT（76.63%），opt 后 15915 个，place 后 15380 个（73.94%），资源已回到 A7-35T 容量内；代价是 DSP 使用 77/90。配置和构建脚本通过 synthesis generic 传入固件的绝对路径，RTL elaboration 已确认 `$readmemh` 成功读取，不再出现 Synth 8-4445。当前 place 后 50 MHz 时序 WNS 为 -7.275 ns，因此资源问题已解决，但时序尚未签核。
