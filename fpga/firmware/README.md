# 当前 FPGA 自检镜像

int8_selftest.hex 是当前 INT8 tile DMA 的 8 KiB 完整镜像，包含训练模型 tile 权重、四个固定 UCI 输入、偏置、参考结果及 RV32I 自检。FC2 使用四组 48B 粗粒度权重包。由 test/int8/firmware.py 的 build 生成；不要使用旧常驻权重窗口或旧 FC2 填充格式的镜像。

配置脚本应将 FPGA_INIT_FILE 设置为此文件在当前机器的绝对路径。非空初始化路径表示 BRAM 在 FPGA 配置时已装载，启动控制器等待后自动放行。
