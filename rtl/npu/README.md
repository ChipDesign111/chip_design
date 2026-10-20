# 最终 W8A4 NPU

| 文件 | 职责 |
| --- | --- |
| [har_stream_top.sv](har_stream_top.sv) | MMIO、两帧DMA暂存、提交、ARM和64槽类别表 |
| [har_stream_core.sv](har_stream_core.sv) | 两级连续发射、隐藏双槽、独立发射/提交/回收 |
| [har_dot_tile.sv](har_dot_tile.sv) | 乘积寄存、分块累加、首尾标记 |
| [har_weight_store.sv](har_weight_store.sv) | 38个同步权重bank、装载/回读和计算读 |

四个模块构成唯一实现，没有INT8激活兼容核心或串行/II20调度模式。输入INT4、隐藏UINT4、权重INT8；FC1为32×4路、FC2为6×2路，另有32路重定标。原8×8 tile接收扩展后的低位宽值，不据此宣称原生INT4面积收益。

规格、修改与测试入口见 [RTL总说明](../README.md)；模型参数见 [部署说明](../../model/README.md)。
