# W8A4 连续流水 RTL 分支

日期：2026-10-20。分支：`feat/npu-w8a4-streaming`。这是可选的新增 RTL 实现，通过 `CHIP_STREAM_NPU` 编译宏启用；未设置时继续使用原 INT8 NPU、原 DMA 与原软件接口。

## 固定硬件规模

| 部分 | 新版规模 |
| --- | --- |
| FC1 | 两个16行×4路tile，整层32×4，共128路点积乘法 |
| FC2 | 一个6行×2路tile，共12路点积乘法 |
| 重定标 | 保留32路并行乘法，不做两路复用或阈值替换 |
| 权重 | INT8常驻，原38个bank/2240 B保持不变 |
| 输入 | 有符号INT4，64维打包为32 B，展开为有符号8 bit后使用原tile |
| 隐藏 | ReLU后UINT4数值0..15，内部零扩展为8 bit供FC2使用 |
| 偏置/累加/得分 | INT32 |

原 `har_dot_tile.sv`、`har_weight_store.sv`、`har_npu_core.sv` 和 `simple_npu_top.sv` 保持原样。新增 [har_stream_core.sv](../rtl/npu/har_stream_core.sv)、[har_stream_top.sv](../rtl/npu/har_stream_top.sv)、[har_stream_dma.sv](../rtl/dma/har_stream_dma.sv)。两处SoC集成文件与AXI元数据适配器增加编译选择/本地信用及提交信号，CPU、AXI库、Debug、时钟和Boot代码不变；集成SHA在manifest中明确更新。

本版低位宽首先减少外部输入流量，复用现有8×8乘法tile，**不宣称已综合成原生4×8乘法阵列或已减半乘法面积**。

## 消除样本间排空空泡

FC1每帧16组，FC2每帧16组。发射完第16组后，调度器允许下一帧的first立即跟随上一帧的last；同步读、乘法和结果寄存器继续处理先前帧。发射进度、隐藏帧提交和最终结果回收使用独立指针/计数，避免把上一帧结果写入当前发射帧的槽。

两个输入槽、两个隐藏槽及两个FC2隐藏快照支持不同帧重叠。FC1可在目标隐藏槽仍被FC2消费时开始下一帧计算，因为该槽在下一次FC1结果写入前已完成16组消费；没有外部FC2停顿路径。模型参数在START时快照，运行时禁止改写。每条命令处理1～64帧，类别结果表保留该批全部结果；它不是无上限流式接口。

最终配置使用MODE=3，充分供数时连续结果间隔为16周期。MODE=0/1是RTL保留的诊断控制，不作为交付性能方案；测试和性能报告统一使用最终配置。SoC仍可能受到SRAM仲裁和供数背压影响。

## DMA与计算并行

```text
8 KiB主SRAM ─32 bit─► DMA读FIFO ─32 bit─► 64 B输入暂存
                        R/W并行             │成功响应后提交1或2帧
                                           ▼
                 两个输入槽 → FC1 → 两个隐藏槽 → FC2 → 批次类别表
```

每个突发最多16个32 bit字，通常搬两条INT4输入；奇数尾帧或4KiB边界可使用8字突发。DMA收到完整正确的RLAST/RRESP并取得OKAY BRESP后，才提交这一突发的1/2条输入；出错则丢弃暂存帧，不把填充的零或错误数据当成有效输入。写突发已发出时仍合法完成AXI事务，错误后本批需软件停止使用并全局复位恢复。

两帧输入暂存为空才授予下一突发信用。预取与计算可以并行，运行时允许DMA写入专用暂存窗口；权重和配置仍有忙时保护。CPU只需一次提交全部输入，DMA自动推进SRAM源地址并重复写同一暂存窗口。DMA FIFO仍为64 B，不需要加宽主SRAM接口。

流模式源地址必须32 B对齐，长度必须是8字整数倍、1～64条输入，整个源范围位于主SRAM。32 B对齐确保4KiB拆分不会切断单条样本。必须先ARM NPU，再启动流DMA；未ARM的流请求被拒绝。一般参数搬运仍要求NPU空闲。CPU不得在DMA完成前修改源数据。

DMA仍使用原0xD00 CSR布局；流模式由DESTINATION=`0x70000E00`选择，WORD_COUNT=`8×样本数`，目的地址每个突发重复，源地址连续。其他参数装载窗口按原布局。AXI库无需改动。

## 寄存器与软件顺序

NPU基址`0x70000000`，以下为字节偏移，所有访问32 bit对齐。

| 偏移 | 读/写 | 内容 |
| --- | --- | --- |
| 0x010 / 0x014 | 读写，仅空闲 | 重新量化M / SHIFT |
| 0x100～0xA57 | 权重/偏置装载 | 沿用原598字布局 |
| 0xD00～0xD1F | DMA CSR | 原布局，新增专用流目的模式 |
| 0xE00～0xE3F | DMA写 | 一/两帧输入暂存；提交由DMA成功响应产生 |
| 0xF00 | 写 | bit0 ARM，清批次计数/状态并快照参数 |
| 0xF04或0x004 | 读 | bit0 DONE、bit1 BUSY、bit2 ERROR |
| 0xF08 | 读写，仅空闲 | 样本数1～64 |
| 0xF0C | 读写，仅空闲 | MODE=0/1/3 |
| 0xF10 | 读 | ARM至最后结果的NPU周期，包含等待首批DMA数据 |
| 0xF14 / 0xF18 | 读 | FC1 / FC2有效发射周期，各应为16×样本数 |
| 0xF1C | 读 | FC1与FC2同时发射周期 |
| 0xF20 / 0xF24 | 读 | 已接收 / 已完成样本数 |
| 0x1000～0x10FF | 读 | 本批64个类别槽；超出已完成范围读0 |

软件先DMA装载598字参数，设置M=39986、SHIFT=24；设置样本数和MODE，ARM；再启动一次输入DMA，轮询DMA和NPU的DONE/ERROR；检查计数并读取类别。轮询必须有超时。输入暂存依赖DMA提交信号，不是可直接由CPU写完后自动启动的普通窗口。完整hidden/score由硬件结果流输出，测试台逐项核对；本批类别由CPU读取并自检。

W8A4的偏置和尺度单独冻结在 [最终量化配置](../model/quantization/w8a4.json)，不覆盖旧model/export。新公式为`hidden=min(15,(max(acc,0)*39986+8388608)>>24)`。原输入尺度、偏置、M=1064不能混用。全2947条参考准确率2490/2947=84.4927%；原INT8为2504/2947=84.9678%，二者数值不同，版本比较使用各自原生数值格式和相同CPU校验工作量。

## 性能和验证

**完整版本主结果：相对前一版52be8c5，统一类别收集/校验口径下整机13619→4972周期，2.739×；装载权重后的处理段11404→3314周期，3.441×。** 两版均已片上存权重，收益来自输入压缩、DMA和调度/驱动整体变化。详情见 [版本间比较](../test/2026-10-20/version-compare/report.md)。

正式结果见 [2026-10-20验证报告](../test/2026-10-20/version-compare/report.md)。测量区分单元连续供数、NPU含DMA等待窗口、端到端流处理窗口和整机总周期。主SRAM同时承担CPU取指与DMA读，不能将核心16周期目标直接称为整机每帧固定16周期。

```sh
python tools/project.py test --suite stream-unit
python tools/project.py test --suite stream-unit --data-root "model/data/UCI HAR Dataset"
python tools/project.py test --suite stream --memory portable-sram --vsim /path/to/vsim
python tools/project.py test --suite stream --memory ra1shd --vsim /path/to/vsim
python test/2026-10-20/scripts/check_stream_synthesis.py --yosys /path/to/yosys
```

第一条适用于公共CI；全模型RTL额外需要官方测试数据。两种SRAM后端的SoC基准使用同一模型/24条真实输入，CPU真实执行RV32I程序，经AXI驱动DMA和NPU；测试台不注入完成状态、不预装NPU权重，只在CPU复位期间通过SRAM端口装载程序。厂商模型采用功能仿真并关闭时序检查，不代表板级实测或物理时序签核。
