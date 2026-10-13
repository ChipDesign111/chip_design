# 共有架构：固定外围与 tiled NPU

2026-10-13；LAB3_PERIMETER_FIXED / HAR_TILED_V2。

外围保持原 Lab 3 字节：CV32E40P、AXI、Debug、Boot RAM、8 KB 主 SRAM、复位、my_soc_top、my_npu_subsystem。90 文件 SHA 校验不变。

```text
platform/course_soc/my_soc_top
    └── my_npu_subsystem（固定 axi2mem / 地址桥）
            └── rtl/npu/{lab3 或 har}/simple_npu_top
                    har:
                    ├── har_weight_store：38 个同步 bank
                    └── har_npu_core
                        ├── 2× har_dot_tile(16,4) → quant → hidden 双缓冲
                        └── 1× har_dot_tile(6,2) → Argmax
```

simple_npu_top 保持 clka/rst_ni/ena/wea/addra[11:0]/dina[31:0]/douta[31:0]。对外围仍为下一拍读有效，32 位对齐写；基址 0x70000000、本地 16 KB、高位别名均保持。

lab3 配置仅用于原 4 位矩阵乘回归，har 配置为 INT8 MLP；同名 top 每次只编译一份。
scripts/run_tests.py 展开冻结原清单并选择实际源，新模块同时进入 HAR_RTL 和 SoC 源列表。没有额外系统顶层。

片上权重容量 2240 B；FC1 32×16×32 bit，FC2 6×8×32 bit。输入、偏置、隐藏及结果为寄存器文件。RAM 阵列不复位，以有效位提供复位后逻辑零行为。双样本共享模型/偏置/量化参数，分开输入/hidden/输出。
原单次 MMIO 布局兼容，新增批长度及第二样本窗口，详见 [MMIO](mmio.md)。

详细 tile 配比、时序、并行与存储见 [tiled-npu.md](tiled-npu.md)，改动流程见 [change-guide.md](change-guide.md)，数值规则见 [numerics.md](numerics.md)。
单样本 39 周期、双样本 59 周期，阶段活跃各 19 周期，重叠 18 周期；不包含 CPU 传输。最终面积/频率/功耗、BRAM/SRAM 宏映射需要目标平台验证。
