# DMA：AXI 接入与输入流搬运

| 文件 | 作用 |
| --- | --- |
| [har_dma_axi.sv](har_dma_axi.sv) | SoC AXI通道/元数据适配；根据CHIP_STREAM_NPU选择引擎 |
| [har_stream_dma.sv](har_stream_dma.sv) | 最终版：独立读写推进、16字FIFO、NPU信用、成功响应后提交 |
| [baseline/har_dma.sv](baseline/har_dma.sv) | INT8兼容引擎：先读完整块，再写入目标窗口 |

CPU配置DMA CSR（NPU基址0x70000000，加偏移0xD00），DMA经AXI从8 KiB主SRAM读数据，再写NPU。它不直接修改权重bank内部信号，也不绕过总线。权重按原598字布局装载一次；最终版输入64维INT4打包成8个32 bit字，最多两条输入/16字突发。

最终版流目的地址是0x70000E00。软件先配置并ARM NPU，再提交1～64条输入的DMA；源地址32 B对齐，长度为8×样本数个字。两帧暂存的信用阻止覆盖；只有完整正确的RLAST/RRESP和OKAY BRESP才提交输入，错误则丢弃暂存帧。32 bit读写总线、FIFO和计算可以重叠，不等于整层权重一次全并行装载。

改最终引擎运行 `python tools/project.py test --suite stream-unit`（248项协议及NPU检查），再跑 `--suite stream --memory portable-sram|ra1shd --vsim /path/to/vsim`。改兼容引擎还需跑 `dma-unit` 和 `dma`。完整协议、错误恢复、接口与性能见 [最终版设计](../../report/streaming.md)；[INT8 DMA说明](../../report/dma.md) 属于兼容路径。
