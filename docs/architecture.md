# System architecture

HAR-NPU 使用固定参考 SoC 和可替换的加速器实现。平台源码与项目 RTL 按来源/修改责任分离，而不是按 HDL 语言分类。

```text
platform/course_soc/soc/rtl/my_soc_top.sv
├── CV32E40P
├── AXI / Debug / Boot RAM / 8 KiB SRAM / Reset
└── my_npu_subsystem.sv
    └── simple_npu_top                 rtl/npu/har/
        ├── har_weight_store          38 synchronous banks
        └── har_npu_core
            ├── 2 × har_dot_tile(16,4)
            ├── ReLU / requantization / hidden double buffer
            └── 1 × har_dot_tile(6,2) → Argmax
```

## 模块与编译配置

| 配置 | 加速器源 | 用途 |
| --- | --- | --- |
| `har` | `rtl/npu/har/` | INT8 64→32→6 MLP |
| `lab3` | `rtl/npu/lab3/` | 4×4、无符号 4-bit 兼容回归 |

两者定义相同的 `simple_npu_top`，每次只编译一份。CPU、互连、系统顶层和 NPU 接入桥共用同一冻结基线，90 文件完整性由 manifest 校验。

加速器保持 `clka/rst_ni/ena/wea/addra[11:0]/dina[31:0]/douta[31:0]`。CPU 字节地址经固定桥转换为 word 地址；基址 `0x70000000`，本地窗口 16 KiB，读下一拍有效，软件只作完整 32-bit 对齐写。具体语义见 [MMIO](mmio.md)。

## 数据与并行

FC1 的 32 个输出通道由两个 16-output/4-lane tile 覆盖；FC2 的 6 个通道由一个 6-output/2-lane tile 覆盖。两层分别发射 16 个 K 维分块，产品与累加打拍。

权重存储为 FC1 32×16×32 bit、FC2 6×8×32 bit，共 2240 B；CPU 回读和计算读取均同步。有效位提供复位后逻辑零行为，RAM 阵列无数据复位。输入、偏置、hidden 和结果为小型寄存器文件。

批次包含 1 或 2 输入，参数共享。双 hidden 缓冲使 FC1 处理下一输入时，FC2 处理上一输入。单输入 39 周期，双输入 59 周期，两层重叠 18 周期；详见 [流水设计](tiled-npu.md)。该实现不包含 DMA 或无限长流。

## 构建与演进

`project.py` 提供统一入口；`scripts/run_tests.py` 展开冻结原清单并选择加速器源，产物位于 `build/`。新增模块需要进入单元和 SoC 源列表。

固定外围、tile 配比和数值边界见 [ADR](adr/README.md)。目标 BRAM/SRAM 宏映射、面积、频率和功耗需要目标平台验证；通用 Yosys 内存统计不代替这些结果。

## 可选 CPU SRAM

rtl/memory 提供 2048×32 单端口主存适配，通过编译配置选择自有行为后端或本地 RA1SHD 模型；外围源码不变，reference 仍为默认。主存宏与 NPU 权重 bank 独立。装载及验证边界见 [SRAM](sram.md)。
