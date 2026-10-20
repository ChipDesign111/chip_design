# 最终版 SoC 架构

`rtl/soc/my_soc_top.sv` 集成CV32E40P、AXI、Debug、Boot、8 KiB主SRAM、流式DMA与W8A4 NPU。`my_npu_subsystem` 直接连接最终NPU，`har_dma_axi` 直接连接最终DMA，无版本选择宏。

```text
CPU / Debug ─┬─ AXI ─► 主SRAM / Boot / NPU MMIO
DMA ─────────┘                    │
主SRAM → DMA读FIFO → 两帧输入暂存 → FC1 → ReLU/量化 → FC2 → 类别表
                                  ↑                     ↑
                               32个权重bank           6个权重bank
```

FC1为32×4路、FC2为6×2路，各16次有效发射；32路隐藏重定标保留。输入INT4、隐藏UINT4、权重INT8，偏置/累加/得分INT32，单命令1～64条。独立输入/隐藏槽及发射、提交、回收状态支持连续样本，理想结果间隔16周期。

主SRAM与CPU/DMA共享AXI；2240 B权重常驻独立的38个同步bank。读、写、计算可以重叠，但总线仲裁与供数背压仍影响整机周期。目录、阅读顺序与修改范围见 [RTL说明](../rtl/README.md)，细节见 [流水设计](streaming.md)。

CPU等外围在rtl/platform，来源与SHA由manifest记录；项目集成文件有明确覆盖记录。旧版设计与复测工具见 [本地归档](local_archive.md)。
