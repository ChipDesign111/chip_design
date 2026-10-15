# Complete SoC RTL

| 路径 | 实现 |
| --- | --- |
| cpu_cv32e40p/ | RISC-V CPU 与 package |
| axi/、common_cells/、include/ | 互连、公共模块和头文件 |
| debug/、clk_rst/ | Debug、时钟与复位 |
| soc/ | my_soc_top 与 NPU 接入包装层 |
| memory/ | Boot 存储、8 KiB 主 SRAM 适配及接口声明 |
| npu/ | 当前 64→32→6 tiled MLP 加速器 |
| filelist.f | 当前 SoC 的统一编译源清单 |
| project.json | 网络、地址和流水参数 |
| manifest.json | 75 个保留外围文件的来源及原字节 SHA-256 |

只编译当前 HAR NPU。主存默认自有行为后端，可选择本地 RA1SHD 模型；不保留旧 NPU 或重复的 my_mainmem。完整说明见 [架构](../report/architecture.md)、[NPU](../report/npu.md) 和 [SRAM](../report/sram.md)。
