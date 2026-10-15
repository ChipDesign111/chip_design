# HAR V2：两级 tile 流水加速器

完整 SoC 外围与 NPU 均位于 rtl，加速器实现在 rtl/npu/。V2 保持整数算术契约，支持双样本模式及计数寄存器，与原单次推理窗口兼容。模型为 64→32→6，输入/权重 INT8、偏置/得分 INT32，ReLU/重新量化只在第一层。

## 为什么 tile 数量 2:1 还不够

第一层 64×32=2048 MAC，第二层 32×6=192 MAC，工作量比为 10.67:1。如果两层使用相同形状和吞吐的 tile，数量 2:1 时第一层仍慢约 5.33 倍。设计采用 2 个 FC1 tile 与 1 个 FC2 tile，通过不同形状平衡阶段吞吐：

| 项目 | 第一级 FC1 | 第二级 FC2 |
| --- | ---: | ---: |
| tile 数 | 2 | 1 |
| 每 tile 输出通道 | 16 | 6 |
| 每 tile 每拍输入元素 | 4 | 2 |
| 每 tile INT8 乘法器 | 64 | 12 |
| 整层 INT8 乘法器 | 128 | 12 |
| 每输出点积长度 | 64 | 32 |
| 每层发射分块数 | 64/4=16 | 32/2=16 |
| 每样本实际活跃周期 | 19 | 19 |

tile 数量比不等于乘法器或面积比。两个 FC1 tile 共 128 个乘法器，FC2 为 12 个；另外还有 32 个量化乘法器。目标面积与频率需要目标平台综合和实现证据。

## 数据通路和真正的流水重叠

```text
输入 slot0 / slot1（各 64 B）
        │
同步权重 RAM → 乘法寄存器 → 归约/累加寄存器
        │   FC1 tile0：输出 0..15
        │   FC1 tile1：输出 16..31
        ↓
32 路 ReLU / 重新量化
        ↓
hidden 双缓冲 slot0 / slot1（各 32 B）
        ↓
同步权重 RAM → 乘法寄存器 → 归约/累加寄存器
        │   FC2 tile：6 个输出
        ↓
有符号 Argmax → 各 slot 的得分/类别 → DONE
```

每个 tile 为 output-stationary：累加器留在 tile 内，权重和输入按 K 维分块进入。FC1 输入广播给 32 个输出通道，FC2 两个隐藏元素广播给 6 个输出。140 个 INT8 乘法器按层独立，不争用一套 MAC。有效位以及首/尾标记随同步读和产品流水传播。

一个输入必须先完成 FC1 才能运行自己的 FC2。真正两级重叠发生在不同样本之间：FC2 处理 slot0 的同时，FC1 处理 slot1。仅把两层代码分成两个模块不能证明存在这种流水。

时序以接受 START 为第 0 拍：

| 周期 | 行为 |
| --- | --- |
| 1–16 | FC1(slot0) 发射 16 组数据 |
| 17–19 | 排空乘积/累加并生成 hidden0 |
| 20 | FC2 接收 hidden0；FC1 已开始 slot1 |
| 21–38 | 两层有效计算区间重叠，统计重叠共 18 拍 |
| 39 | slot0 得分/类别完成；单样本在此 DONE |
| 40 | FC2 接收 hidden1 |
| 59 | slot1 完成；双样本整体 DONE |

FC1 第二个样本从第 20 拍发射，第 38 拍生成 hidden1；FC2 第一帧从第 21 拍发射，第 39 拍完成。两个 stage 各样本活跃 19 拍；stage2 交接留 1 拍，因此两帧结果间隔 20 拍。
当前最多一次命令两帧；另有 [DMA](dma.md) 负责主 SRAM→NPU 装载，尚未实现无限长流或装载/计算重叠。

## 片上存储

[har_weight_store.sv](../rtl/npu/har_weight_store.sv)：

- FC1：32 个 bank，每 bank 16×32 bit，共 2048 B；每拍各 bank 读一个含四 INT8 权重的 word。
- FC2：6 个 bank，每 bank 8×32 bit，共 192 B；每拍取 word 的低/高 16 bit，供两个输入 lane。
- 每 bank 计算端和 CPU 回读端均为同步读；CPU 可在两层同时计算时读回权重。
- CPU 写仅在整个 NPU 空闲时允许，避免计算与装载冲突。
- RAM 数据阵列无复位；560 个有效位复位为零，未装载的 word 逻辑读零。复位后必须重新装载模型。
- 输入、偏置、hidden 双缓冲及结果仍为小型寄存器文件。权重装载一次可跨多个命令复用。

Yosys 通用综合结构检查保留 38 个 RAM、17920 bit 和 76 个同步读端口，不等于已映射到 FPGA BRAM 或 ASIC SRAM 宏。很浅的小 bank 可能映射为分布式 RAM；最终选择需用目标平台综合验证。同步 RAM 编码原则可参考 [AMD UG901](https://docs.amd.com/r/en-US/ug901-vivado-synthesis)。

## 对应代码

| 文件 | 职责 |
| --- | --- |
| [har_dot_tile.sv](../rtl/npu/har_dot_tile.sv) | 参数化 tile，寄存乘积、分块累加、首尾标记 |
| [har_weight_store.sv](../rtl/npu/har_weight_store.sv) | 双读端口 bank 存储、CPU 装载/回读、有效位 |
| [har_npu_core.sv](../rtl/npu/har_npu_core.sv) | 2:1 tile 实例、两级调度、hidden 双缓冲、计数 |
| [simple_npu_top.sv](../rtl/npu/simple_npu_top.sv) | 保持 SoC 接入端口、MMIO 和同步读返回 |
| [tb_har_core.sv](../test/2026-10-15/rtl/tb_har_core.sv) | 1000 组各跑单次/双次，共 3000 推理 |
| [tb_har_mmio.sv](../test/2026-10-15/rtl/tb_har_mmio.sv) | 单次/双次装载、忙时保护、重叠时权重回读 |
| [build_har_firmware.py](../test/2026-10-15/scripts/build_har_firmware.py) | CPU 六个单次 + 一批两个输入，逐项检查及周期断言 |
| [check_synthesis.py](../test/2026-10-15/scripts/check_synthesis.py) | 无工艺库的综合结构、RAM/乘法器/锁存器检查 |

## 验证和限制

整数参考未改变。每个输出和中间值逐项一致，测试独立观察两个 stage 的同时活跃拍数，再与计数寄存器比较。复位覆盖 FC1、FC2 和真实重叠区间。完整 SoC 使用真实 CV32E40P 通过 AXI 发 MMIO，由当前 tb_soc 被动观察 CPU 完成写。

```text
python tools/project.py check
python tools/project.py test --suite unit
python tools/project.py test --suite model
python tools/project.py test --suite soc --vsim /path/to/vsim
python tools/project.py synth
```

最后一项需要 Yosys，可用 --yosys 指定路径。未访问 PDK/标准单元库。实际结果及同工作量性能比较见 [V2 报告](../test/2026-10-13/tiled-v2/report.md)；初始 V1 报告作为历史版本保留。

真实模型另有全量 2947 条 RTL 逐值对照及 24 条 CPU / SoC 自检，见 [开发与模型验证](development.md) 和 [真实模型报告](../test/2026-10-13/real-model/report.md)。板级验证与物理签核尚未完成。
