# SoC architecture

```text
rtl/soc/my_soc_top.sv
├── rtl/cpu_cv32e40p       CV32E40P
├── rtl/axi               AXI interconnect / axi2mem
├── rtl/debug             JTAG / Debug
├── rtl/clk_rst           clock / reset
├── rtl/memory            Boot + 2048×32 main SRAM
└── rtl/soc/my_npu_subsystem.sv
    └── rtl/npu/simple_npu_top.sv
        ├── har_weight_store  38 synchronous banks
        └── har_npu_core      FC1 tiles ×2 → ReLU/requant → FC2 tile ×1 → Argmax
```

## 硬件边界

rtl 包含完整硬件，没有独立 platform 目录。rtl/filelist.f 是当前 SoC 的源清单；运行工具展开绝对路径并加入测试顶层，不再从旧课程清单替换 NPU。

CPU、AXI、Debug、时钟/复位与 Boot 外围共 75 个保留文件的来源记录在 rtl/manifest.json。三个文件有附原哈希的集成修改：两个既有 DMA 集成文件中，SoC 顶层新增下降沿复位释放寄存器；bootram 首条指令改为等待下载，见 [启动与复位协议](../eda/BOOT_PROTOCOL.md)。其余 72 个保持原始课程字节。原 90-file 清单中的旧主存行为实现、原始测试、启动材料及旧 filelist 已退出当前源码。当前 NPU 是唯一加速器实现，旧 4×4 NPU 不再参与任何构建。

## 模型与算术

MLP 为 64→32→6，2278 参数、2240 MAC/输入；输入/权重 INT8，偏置/累加/得分 INT32，hidden 为 0..127。第一层 ReLU + 整数量化，第二层有符号 Argmax，相等取较小下标。规则见 [model/numerics.md](../model/numerics.md)。

两 FC1 tile 各 16 输出×4 lane；FC2 为 6 输出×2 lane。每级发射 16 块，独立乘法/累加流水及 hidden 双缓冲支持跨样本重叠。单输入 39 周期、两输入 59 周期、重叠 18 周期；详见 [NPU](npu.md)。

## 存储与接口

CPU 主存 8192 B，基址 0x80000000；程序状态区 0x80001FE0–0x80001FFF。历史不含搬运基准的真实模型 24 条自检镜像占 6232 B；EDA 使用独立固定的 CPU/DMA 基准镜像，来源和哈希见 [固件清单](../eda/sim/firmware/manifest.json)。主存后端只改变实现选择，不改变容量、字节写使能与一拍读接口。

NPU 基址 0x70000000，本地窗口 16 KiB；word 地址 12 bit，软件完整 32-bit 对齐访问。权重 2240 B 分在 38 个同步 bank，CPU 回读与计算读独立。单端口主 SRAM 不替代并行权重 bank。寄存器见 [MMIO](mmio.md)。

## 修改范围

- rtl/npu：允许优化 tile、调度和存储；同步更新数值/接口、固件和测试。
- rtl/memory：允许后端适配，保持主存协议；原外围更新须独立记录来源和校验迁移。
- rtl 其余保留外围：非日常修改区，由 tools/check_hardware.py 校验。
- model：模型、特征或量化改变后需重新导出与真实数据评估。
- test/日期：每轮验证脚本、testbench、输入、结果与报告。
- fpga：当前为空，尚未交付目标实现。
- eda：完整 SoC 的 TSMC180 工艺综合及前后仿流程，见 [EDA](../eda/README.md)；布局布线、CTS 和课程 TT 下的布线后验证已完成，见 [物理实现结果](../eda/pnr/RESULTS.md)。

完整功能仿真不等于 FPGA 上板或 ASIC 签核。当前支持 SRAM→NPU 的独立 AXI burst DMA，程序通过顶层 JTAG 的 DMI/SBA 路径下载和启动，见 [启动协议](../eda/BOOT_PROTOCOL.md) 与 [EDA 结果](../eda/RESULTS.md)。尚无搬运/计算重叠或无限长队列，见 [DMA](dma.md)。
