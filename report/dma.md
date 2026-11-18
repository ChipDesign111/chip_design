# 当前DMA与数据交接

har_dma是AXI4增量突发引擎，har_dma_axi适配总线元数据。两字FIFO使读写独立推进并支持背压；每次突发最多16字，跨4KiB自动拆分。完成以最后写响应B握手为准。

顺序任务引擎使用同一DMA读取任务描述符、输入、bias、权重和LUT，并从NPU打包窗口写回INT8结果。末字使用字节掩码，输出最后一个B成功后才发布有效状态。CPU手工DMA仍受原地址范围保护；任务专用入口由内部控制，不扩大手工DMA权限。

权重bank只有两个64B；本批所有样本使用完后才释放。块必须完整接收、DMA完成且无错误才发布。错误事务按AXI协议排空，不把失败块交给MAC。读/写响应错误和异常RLAST均有定向回归；失联对端仍须最终响应，硬件不臆造完成。

原MODE=0每批读取2048B W1及192B有效W2，共36次权重DMA，与batch无关。通用FC每tile搬运16×ceil(N/8)字节，输入K尾部/输出N尾部按有效范围处理；具体描述符及流量见[任务ABI](../compiler/TASK_ABI.md)和[实测分解](results/performance/README.md)。

调试CSR位于NPU+0xd00：CONTROL、STATUS、源、目的、字数、周期、复制字数、错误码。正常新编译程序由任务引擎自动提交DMA，不依赖CPU逐tile调度。
