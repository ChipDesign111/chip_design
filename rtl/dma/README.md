# 最终流式 DMA

[har_stream_dma.sv](har_stream_dma.sv) 是唯一搬运引擎；[har_dma_axi.sv](har_dma_axi.sv) 直接接入SoC AXI，不再按宏选择旧引擎。

CPU配置0x70000D00的DMA寄存器，经32 bit总线从8 KiB主SRAM读数据并写NPU。权重/偏置共598字，输入每条8字。16字FIFO与两帧输入暂存允许读、写、计算重叠；仅收到正确RLAST/RRESP及OKAY BRESP后提交输入，错误不提交。

软件先配置并ARM NPU，再搬运1～64条输入到0x70000E00；源32 B对齐、长度为8×样本数个字。信用防止覆盖未消费的包。运行 `python tools/project.py test --suite unit`、双后端 `soc` 及 `synth`。协议与异常恢复见 [设计](../../report/streaming.md)。
