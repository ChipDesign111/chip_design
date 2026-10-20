# Lab3 外围与主存适配

这一层提供 NPU 运行所需的 CPU、互连、Debug、时钟/复位、Boot 和主 SRAM。SoC 顶层在 [../soc](../soc/README.md)，本层不再复制一份顶层或 NPU。

| 目录 | 用途 | 修改边界 |
| --- | --- | --- |
| cpu_cv32e40p/ | CV32E40P 核、package、内部模块 | 保留提供源码与原版权 |
| axi/ | 互连、地址译码、总线桥 | 保留提供源码；项目 DMA 适配在 ../dma |
| common_cells/ | FIFO、仲裁、CDC、寄存器等 | 保留提供源码 |
| include/ | AXI 宏、公共头和 SoC package | 编译包含目录，不单独作为产品模块 |
| debug/ | JTAG、Debug Module 与 Debug ROM | 保留提供源码 |
| clk_rst/ | 时钟门控、复位同步 | 保留提供源码 |
| [memory/](memory/README.md) | Boot 与主 SRAM | Boot 为保留源码；主存适配为项目维护代码 |

保留外围以 [manifest.json](../manifest.json) 的具体文件记录为准，不能仅凭目录判定所有文件都不可修改。`memory/my_mainmem.sv`、`chip_sram_2048x32.sv` 和 `ra1shd_blackbox.sv` 是项目主存适配/声明。修改后运行 SRAM 双后端测试与 SoC 集成测试。

本次仅迁移路径，SystemVerilog 内容和模块名不变。来源、版权与字节 SHA 保留，包含目录由 [filelist.f](../filelist.f) 统一维护。厂商 SRAM 模型、PDK 和库文件不放在这里；本地模型路径见 [SRAM说明](../../report/sram.md)。
