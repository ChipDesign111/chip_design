# SoC 架构与代码边界

完整硬件在 `rtl/`，按集成、外围、计算与搬运四类组织。模块逐项说明、阅读顺序和修改/验证矩阵以 [RTL入口](../rtl/README.md) 为准。

```text
rtl/soc/my_soc_top.sv
├── rtl/platform/       CPU、AXI、Debug、时钟/复位、Boot、主SRAM
├── rtl/dma/har_dma_axi.sv
│   ├── CHIP_STREAM_NPU：har_stream_dma
│   └── 默认：baseline/har_dma
└── rtl/soc/my_npu_subsystem.sv
    ├── CHIP_STREAM_NPU：npu/har_stream_top → har_stream_core
    └── 默认：npu/baseline/simple_npu_top → har_npu_core
        两版均使用 npu/common/ 的 tile 与权重bank
```

## 配置与算术

当前开发使用W8A4连续流水配置：INT4输入、ReLU后UINT4、INT8权重和INT32偏置/累加/得分，单命令1～64条样本，供数充分时结果间隔16周期。FC1为32×4路、FC2为6×2路，另有32路重定标乘法。参数、接口与精度见 [最终版设计](streaming.md)。

未定义CHIP_STREAM_NPU时仍构建INT8兼容路径，最多两条输入；39/59周期是该兼容核心的单/双样本值，不能用于描述最终版整机吞吐。两版的模块、DMA和测试入口在 [project.json](../rtl/project.json) 的profiles中明确区分。

## 存储与数据流

主SRAM为8192 B，基址0x80000000，CPU与DMA通过AXI共享。主存后端可以选择portable-sram或本地授权ra1shd，接口容量、掩码写和读时序保持相同。NPU位于0x70000000的16 KiB窗口，其2240 B权重由38个独立同步bank保存；片上权重读不会经由主SRAM。

最终版先搬运598字权重/偏置，再以8字/样本搬运打包输入。DMA使用最多16字FIFO和两帧暂存，输入只在成功响应后提交；计算与下一批预取可以重叠。结果按帧顺序写入类别表。完整SoC基准中CPU真实执行固件并检查类别，测试台同时核对hidden/score/class。

## 来源与修改边界

CPU、AXI、Debug、时钟/复位和Boot来源及SHA在 [manifest](../rtl/manifest.json) 中；两个soc集成文件有明确的项目覆盖记录。本次目录整理只迁移路径，所有SystemVerilog源码字节不变。新增主存适配和NPU/DMA是项目维护代码，具体修改与检查见 [RTL入口](../rtl/README.md)。

`rtl/platform` 是硬件外围子目录；`fpga/` 和 `eda/` 是实现工程目录，当前仍为空占位。功能仿真与通用综合不等于FPGA上板、目标面积/功耗或ASIC时序与物理签核。
