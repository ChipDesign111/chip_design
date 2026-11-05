# 流式权重 DMA

har_dma：独立 AXI 读写通道，两字 FIFO、突发边界拆分及错误处理。
har_dma_axi：AXI_BUS 元数据适配；USER=1 标记 DMA 写入。
正常推理由 NPU 自动提交描述符。见 [DMA](../../report/dma.md)。
