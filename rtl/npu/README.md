# NPU：最终流水实现与共享计算单元

当前开发入口是 [har_stream_top.sv](har_stream_top.sv) 和 [har_stream_core.sv](har_stream_core.sv)。模型固定64→32→6，输入INT4、隐藏UINT4、权重INT8、偏置/累加/得分INT32。ReLU后重定标，再送入FC2，最后Argmax输出六类之一。

| 文件/目录 | 负责什么 |
| --- | --- |
| har_stream_top.sv | MMIO、两帧DMA输入暂存、成功提交、ARM、批次类别表 |
| har_stream_core.sv | FC1/FC2连续调度、输入/隐藏双槽、独立发射/提交/回收状态 |
| [common/har_dot_tile.sv](common/har_dot_tile.sv) | 点积tile：乘积寄存、分块累加、首尾标记 |
| [common/har_weight_store.sv](common/har_weight_store.sv) | 38个同步权重bank，CPU装载/回读与计算读 |
| [baseline/](baseline/README.md) | INT8兼容核心和MMIO包装，不是另一套最终方案 |

FC1两个16行×4路tile，共128路点积乘法；FC2为6行×2路，共12路；另保留32路重定标。两层各需16次有效发射，供数充分时连续结果间隔16周期。低位宽值展开后复用现有8×8 tile，因此不能仅凭INT4输入推断乘法面积减半。权重bank共2240 B，与主SRAM分开。

定义 `CHIP_STREAM_NPU` 后由 [SoC包装](../soc/my_npu_subsystem.sv) 选择最终版，输入由 [流式DMA](../dma/har_stream_dma.sv) 搬运；不定义时实例化baseline。两版模型偏置和重定标参数不同，最终配置只读 [w8a4.json](../../model/quantization/w8a4.json)。

改最终调度或MMIO后，运行 `python tools/project.py test --suite stream-unit`，再跑 `--suite stream --vsim /path/to/vsim`。改common文件还须跑INT8的 `unit`、`model`、综合及完整SoC。全模型输入、DMA异常、两种SRAM的命令见 [RTL总说明](../README.md)。接口与流水细节见 [连续流水设计](../../report/streaming.md)；[INT8设计](../../report/npu.md) 仅说明兼容路径。
