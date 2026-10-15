# SRAM-to-NPU DMA

DMA 是独立 AXI4 主设备，从 8 KiB CPU 主 SRAM 搬运权重、偏置或输入到现有 NPU 地址窗口。CPU 设置源、目的、word 数并启动，DMA 自主完成读写；当前不搬运结果、不自动启动 NPU，也不实现计算与搬运重叠。

## 结构

```text
CPU / Debug / DMA → AXI crossbar → 主 SRAM / NPU MMIO
                    DMA：最多 16-word 读突发
                         → 16×32-bit 缓冲
                         → 16-word 写突发
```

每次只有一个未完成突发，先读完整块再写；尾块取剩余 word 数，并在 4 KiB 边界截断。AW/W 通道独立握手，所有 valid 在背压下保持地址/数据稳定。每个读响应检查 RRESP 和 RLAST，每个写响应检查 BRESP；错误不继续提交下一突发。复位同时复位 DMA 和互连以中止在途事务。

DMA 核心为 [har_dma.sv](../rtl/dma/har_dma.sv)，AXI 元数据适配为 [har_dma_axi.sv](../rtl/dma/har_dma_axi.sv)。通用综合保留 512-bit 缓冲和 343 bit 显式寄存器，无乘法器或锁存器；此统计不含新增 AXI 路由资源，不能作为物理面积。

## CSR

DMA CSR 位于 NPU 基址 `0x70000000 + 0xD00`，32-bit 对齐访问。其他 NPU 寄存器及算术行为不变。

| DMA 相对偏移 | 名称 | 行为 |
| --- | --- | --- |
| 0x00 | CONTROL | bit0 START，bit1 ACK；同时置位时 START 优先，读零 |
| 0x04 | STATUS | bit0 DONE，bit1 BUSY，bit2 ERROR；读无副作用 |
| 0x08 | SOURCE | SRAM 源字节地址，4-byte 对齐 |
| 0x0C | DESTINATION | NPU 目的字节地址，4-byte 对齐 |
| 0x10 | WORD_COUNT | 32-bit word 数，非字节数 |
| 0x14 | CYCLES | 接受合法启动至完成的 DMA 活跃周期 |
| 0x18 | WORDS_COPIED | 已收到 OKAY 写响应的 word 数 |
| 0x1C | ERROR_CODE | 1 地址/长度；2 NPU busy；4 读响应；5 RLAST；6 写响应；7 忙时写/主机冲突 |

START 在空闲时清旧计数、DONE 和 ERROR，并验证完整地址范围。非法配置立即 DONE+ERROR，不发 AXI 请求。ACK 在空闲时清 DONE/ERROR，保留计数；busy 时 CSR 写忽略并置 ERROR，当前传输继续。错误响应终止时可能已有部分写入，不能视为事务回滚。

允许源范围为 `[0x80000000, 0x80002000)`，完整传输必须落在范围内。目的只能完整落在一段合法窗口：

- 参数 `[0x70000100, 0x70000A58)`：560 个权重 word + 38 个偏置 word。
- 输入0 `[0x70000040, 0x70000080)`。
- 输入1 `[0x70000C00, 0x70000C40)`。

不允许目的指向 CONTROL、结果或 DMA CSR。NPU busy 时不能启动 DMA。DMA 写以 AXI USER=1 标记；DMA busy 时未标记主机对 NPU 的写请求被阻止，并置 DMA ERROR=7。CPU 可读状态，但不得在完成前修改源数据。这里 USER 是受控片上主设备的来源标记，不是安全隔离机制。

软件必须有有界超时轮询；当前没有硬件事务超时、取消或中断。缺失 AXI 响应会保持 busy，复位前应确保全互连同步复位，不能仅单独撤销已发事务。

## 实测方法

```sh
python tools/project.py test --suite dma-unit
python tools/project.py test --suite dma --memory portable-sram --vsim /path/to/vsim
python tools/project.py test --suite dma --memory ra1shd --vsim /path/to/vsim
```

公开 CI 运行协议/入口单元测试和通用综合；完整商业 SoC 基准本地运行。两份 RV32I 程序使用同一硬件、模型、24 条真实输入和逐值结果检查，只改变装载方式。搬运 598 个参数 word 和 384 个输入 word，12 个双样本批次。

固件读取 mcycle，分别记录参数装载、累计输入装载和应用总周期；测试顶层另记录启动至 CPU 完成标志的 SoC 周期。搬运时间包含描述符设置、轮询和完成检查；应用时间包含相同的 hidden/score/class 检查。测试顶层被动统计真实 DMA AXI 数据拍及突发，不强制完成标志。

两种 SRAM 后端均得到：参数 29330→1872 周期，输入 19656→6960 周期，总搬运 48986→8832 周期（5.55×），SoC 76725→36571 周期（2.10×）。权重已装载后的推理/校验段为 47067→34371 周期（1.37×）。发布证据以 [DMA 验证报告](../test/2026-10-15/dma/report.md) 中最终源 SHA 和两种后端复测为准。

NPU 每批仍为 59 周期，39/59/18 核心契约不变。DMA 加速来源是批量搬运及减少 CPU 指令取数开销，不是算术核心提速。小输入的描述符开销使其收益低于大参数块。当前为功能仿真周期；厂商 SRAM SoC 仍显式关闭时序检查，不代表目标频率或 STA/SDF 签核通过。

## 基线更新

新增 DMA 要求四个 AXI 发起端（原为 CPU 指令、CPU 数据、Debug 三个）；地址目标仍是原四个。项目集成文件 my_soc_top/my_npu_subsystem 明确更新，manifest 保存其旧 SHA 和修改理由。CPU、AXI 库、Debug、时钟、Boot 代码及 NPU 点积/权重/调度核心不改写。simple_npu_top 增加内部 busy 状态输出，现有 MMIO 端口和寄存器行为兼容。
