# SoC memory

bootram / bootrom 为保留外围。my_mainmem + chip_sram_2048x32 实现 8192 B 主存：默认 portable-sram，授权本地环境可选 ra1shd。ra1shd_blackbox 仅为自主编写的连接声明，不含厂商内容。

主存不因复位擦除，上电内容未定义，仿真镜像通过 TB 端口装载。NPU 权重 bank 是独立存储。见 [SRAM](../../report/sram.md)。
