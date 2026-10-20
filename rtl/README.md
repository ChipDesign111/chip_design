# RTL：从哪里读、改哪里、怎么验证

这里包含完整的 CV32E40P + AXI + 64→32→6 MLP SoC。当前开发实现是 **W8A4 连续流水 NPU + 流式 DMA**；INT8 实现保留为兼容路径和性能对比基线。二者共用 CPU、总线、主 SRAM、tile 和权重 bank。

## 目录只有四块

```text
rtl/
├── soc/                         项目集成：SoC 顶层、NPU/DMA 接入
├── platform/                    Lab3 外围和主存适配
│   ├── cpu_cv32e40p/            CPU 源码和 package
│   ├── axi/                     AXI 互连和桥
│   ├── debug/                   JTAG / Debug
│   ├── clk_rst/                 时钟与复位
│   ├── common_cells/            通用 FIFO、仲裁、CDC 等
│   ├── include/                 AXI 宏、公共头文件和 SoC package
│   └── memory/                  Boot、8 KiB 主 SRAM 和后端适配
├── npu/                         NPU 算法硬件
│   ├── har_stream_top.sv         最终版 MMIO、输入包和结果表
│   ├── har_stream_core.sv        最终版两级连续流水调度
│   ├── common/                  两版共用的 tile 和权重 bank
│   └── baseline/                INT8 core / MMIO 包装
├── dma/                         SRAM→NPU 数据搬运
│   ├── har_dma_axi.sv            SoC AXI 接口适配和引擎选择
│   ├── har_stream_dma.sv         最终版读写流水、信用与成功提交
│   └── baseline/har_dma.sv       INT8 兼容搬运引擎
├── filelist.f                   唯一 SoC 源清单，保留 package 编译顺序
├── project.json                 两种构建配置、网络、地址和参数
└── manifest.json                保留外围的来源、迁移路径和 SHA-256
```

`platform` 是 `rtl` 内的硬件子目录，不是另一份 SoC。测试放在仓库的 `test/`；FPGA/后端工程分别放在 `fpga/`、`eda/`。

## 先读这五个文件

| 顺序 | 文件 | 需要看懂的内容 |
| --- | --- | --- |
| 1 | [soc/my_soc_top.sv](soc/my_soc_top.sv) | CPU、Debug、DMA 三类主设备如何共享 AXI 与主 SRAM |
| 2 | [soc/my_npu_subsystem.sv](soc/my_npu_subsystem.sv) | NPU 地址窗口、DMA CSR、访问保护和编译选择 |
| 3 | [dma/har_stream_dma.sv](dma/har_stream_dma.sv) | 输入从 SRAM 搬到 NPU，什么条件才允许提交 |
| 4 | [npu/har_stream_top.sv](npu/har_stream_top.sv) | MMIO 配置、打包输入、ARM 和批次结果 |
| 5 | [npu/har_stream_core.sv](npu/har_stream_core.sv) | FC1→ReLU/量化→FC2→Argmax 与跨样本重叠 |

随后读 [tile](npu/common/har_dot_tile.sv) 和 [权重存储](npu/common/har_weight_store.sv)。当前 FC1 为32×4路、FC2为6×2路，另有32路重定标乘法；38个权重 bank 共2240 B，装载一次后复用。完整原理与时序见 [连续流水设计](../report/streaming.md)。

## 哪一版会被编译和实例化

| 配置 | 选择方法 | NPU / DMA | 输入、隐藏 | 验证入口 |
| --- | --- | --- | --- | --- |
| 最终开发版 stream | 定义 `CHIP_STREAM_NPU` | `har_stream_top` / `har_stream_dma` | INT4 / UINT4，1～64条一批 | `--suite stream` |
| 兼容版 int8 | 不定义上述宏 | `simple_npu_top` / `har_dma` | INT8 / 0..127，最多2条一批 | `--suite model-soc` |

目录归档不改变默认构建行为。`filelist.f` 列出两版的模块定义，`soc/` 和 AXI 适配器根据宏只实例化对应引擎。`stream` 测试自动添加宏；直接使用 EDA 工具时，从仓库根目录读取 `rtl/filelist.f` 并自行设置宏。不要把两版的偏置、重定标参数或输入编码混用；最终版参数在 [w8a4.json](../model/quantization/w8a4.json)。[project.json](project.json) 的旧顶层数值字段属于兼容版，`profiles` 明确列出两种配置。

## 能改什么，改完验证什么

| 修改位置 | 可以做什么 / 必须保持什么 | 至少运行 |
| --- | --- | --- |
| `npu/har_stream_*.sv` | 改调度、输入槽、结果回收；保持帧顺序和数值契约 | `stream-unit`，再跑 `stream` 完整 SoC |
| `npu/common/` | 改 tile 或 bank；两版共同依赖 | `stream-unit`、`unit`、`model`、两版综合及 SoC |
| `dma/har_stream_dma.sv` | 改预取、突发、信用；错误包不得提交，AXI 事务须合法完成 | `stream-unit`，再跑双 SRAM 的 `stream` |
| `soc/`、`dma/har_dma_axi.sv` | 改集成或接口；同步寄存器说明、保护规则和来源记录 | `check`、两版完整 SoC |
| `platform/memory/` 的主存适配文件 | 改主存后端；保持8 KiB容量、掩码写和读时序 | `memory` 双后端、两版完整 SoC及 SRAM 综合 |
| `platform/` 中的 CPU/AXI/Debug/时钟/Boot | 课程提供的外围，日常优化无需改；确需改动应记录来源及 SHA 变化 | `check` 和全部受影响回归 |
| `npu/baseline/`、`dma/baseline/` | INT8 兼容路径维护；最终版优化主要在上面几行 | `unit`、`model`、`dma-unit`、INT8 完整 SoC |

`manifest.json` 校验75个保留文件；其中2个 `soc/` 文件已有明确记录的项目接入修改。其余来源与字节 SHA 保持可追溯。新增模块需加入 `filelist.f`，还需加入相关核级测试和综合脚本的源列表，不能只把文件放进目录。

## 验证命令

以下命令从仓库根目录运行。`stream-unit` 用 Icarus + NumPy；完整 SoC 用 ModelSim；综合结构检查用 Yosys。工具不在 PATH 时增加 `--iverilog`、`--vvp`、`--vsim` 或 `--yosys` 的路径。

```sh
python tools/project.py check
python tools/project.py test --suite stream-unit
python tools/project.py test --suite stream --memory portable-sram --vsim /path/to/vsim
python tools/project.py test --suite stream --memory ra1shd --vsim /path/to/vsim
python tools/project.py test --suite stream-unit --data-root "model/data/UCI HAR Dataset"
python tools/project.py test --suite unit
python tools/project.py test --suite model
python tools/project.py test --suite dma-unit
python tools/project.py synth
python test/2026-10-20/scripts/check_stream_synthesis.py --yosys /path/to/yosys
```

`stream-unit` 包含248项DMA协议检查、24条模型逐值对照和包错误/乱序/复位检查；带数据集参数时增加全部2947条模型输入。`stream` 先跑上述核级验证，再将前一版真实INT8 RTL与当前完整SoC分别编译，CPU执行并校验同一批24条输入；两版的hidden、score、类别都由测试台核对。授权 SRAM 资料只从忽略的 `tools/local/vendor/` 读取。

最终证据见 [版本比较](../test/2026-10-20/version-compare/report.md) 和 [功能/结构结果](../test/2026-10-20/validation.json)。这些是功能仿真与通用结构检查；FPGA、目标工艺面积和时序签核另需对应实现流程。
