# 最终版 RTL

本目录只包含一套W8A4连续流水SoC。顶层直接实例化最终NPU与DMA，不需要 `CHIP_STREAM_NPU`，也没有common/baseline兼容目录。

```text
rtl/
├── soc/                       SoC顶层与NPU/DMA接入
├── platform/                  课程CPU、AXI、Debug、时钟、Boot和主存
├── npu/
│   ├── har_stream_top.sv       MMIO、输入暂存和批次类别表
│   ├── har_stream_core.sv      连续两级调度、ReLU/量化、Argmax
│   ├── har_dot_tile.sv         最终版点积tile
│   └── har_weight_store.sv     最终版38个权重bank
├── dma/
│   ├── har_stream_dma.sv       读写流水、信用、成功响应后提交
│   └── har_dma_axi.sv          AXI通道与元数据适配
├── filelist.f                 唯一SoC编译清单
├── project.json               唯一硬件规格与地址布局
└── manifest.json              课程外围来源、SHA和项目接入修改
```

先读 [my_soc_top](soc/my_soc_top.sv)，了解CPU、Debug和DMA共享AXI/主SRAM；再读 [my_npu_subsystem](soc/my_npu_subsystem.sv) 的寄存器和访问保护，随后读 [DMA](dma/har_stream_dma.sv)、[NPU包装](npu/har_stream_top.sv) 和 [核心](npu/har_stream_core.sv)。

FC1两个16×4 tile，共128路点积乘法；FC2为6×2，共12路；另有32路重定标乘法。两层各发射16次，供数充分时结果间隔16周期。权重INT8、输入INT4、ReLU后UINT4、偏置/累加/得分INT32。2240 B权重常驻独立bank，与8 KiB主SRAM分开。

| 改动 | 位置 | 验证 |
| --- | --- | --- |
| tile、bank或流水调度 | npu/ | unit、完整2947条模型、soc、synth |
| DMA突发、FIFO、信用与异常 | dma/ | unit（含248项DMA检查）、双后端soc、synth |
| 地址、端口或接入保护 | soc/ | check、unit和双后端soc；更新manifest覆盖记录 |
| 主存适配 | platform/memory/ | 双后端memory、soc及synth |
| 课程CPU/AXI/Debug/时钟/Boot | platform/ | 按manifest保留来源与字节，确需修改时记录并回归 |

从仓库根目录运行：

```sh
python tools/project.py check
python tools/project.py test --suite unit
python tools/project.py test --suite unit --data-root "model/data/UCI HAR Dataset"
python tools/project.py test --suite memory
python tools/project.py test --suite soc --memory portable-sram --vsim /path/to/vsim
python tools/project.py test --suite soc --memory ra1shd --vsim /path/to/vsim
python tools/project.py synth --yosys /path/to/yosys
```

核级测试用Icarus和NumPy；SoC用ModelSim；综合用Yosys。`filelist.f` 从仓库根目录使用，无需版本选择。完整数值/流水与寄存器见 [设计说明](../report/streaming.md)、[MMIO](../report/mmio.md)。旧版在 [仓库外的本地归档](../report/local_archive.md)，不参与当前构建。
