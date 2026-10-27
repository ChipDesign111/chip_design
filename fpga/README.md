# 从 main 保留的 Vivado 工程

本分支主要验证服务器 TSMC180 ASIC 流程。保留 main 更新的 Vivado 2019.1 工程、A7-35T 引脚和时钟生成配置；当前 filelist 及 firmware/int8_selftest.hex 已适配 INT8 tile DMA。

使用 configure_final_project.tcl 重新生成源清单，并将 INIT_FILE 改为当前机器的绝对路径，再构建。旧并行架构在 main 的 LUT 超限结论属于旧实现；本分支没有重新宣称板上运行或 Vivado 面积已验证。固件从 test/int8/firmware.py 生成，CPU 通过 MMIO 做训练模型八个样本自检。
