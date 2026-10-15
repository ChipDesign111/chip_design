# MMIO register reference

状态：HAR_TILED_V2，2026-10-13。旧单次窗口兼容；新增批长度、第二样本与流水计数。当前 SoC 仅保留 HAR 地址表。
基址 0x70000000，全部采用 32 位对齐字访问。本地窗口 0x4000 字节。

## 寄存器

| 偏移 | 名称 | 实现行为 |
| --- | --- | --- |
| 0x0000 | CONTROL | bit0 START，bit1 ACK_DONE；其余保留 |
| 0x0004 | STATUS | bit0 DONE，bit1 BUSY，bit2 ERROR；读取无副作用 |
| 0x0008 | CLASS_ID | 完成后返回 0–5 |
| 0x000C | CYCLE_COUNT | 接受启动至完成的计算周期 |
| 0x0010 | REQUANT_MULT | 0–65535，复位默认 1 |
| 0x0014 | REQUANT_SHIFT | 0–31，复位默认 0 |
| 0x0018 | BATCH_COUNT | 可写 1 或 2，默认 1；非法值保留旧值并置 ERROR |
| 0x001C | OVERLAP_CYCLES | 两级同时活跃的拍数，单次 0、双次 18 |
| 0x0020 | FC1_ACTIVE_CYCLES | 单次 19、双次 38 |
| 0x0024 | FC2_ACTIVE_CYCLES | 单次 19、双次 38 |

START 在空闲/已完成时接受，清旧 DONE、ERROR 并开始计算；BUSY 时所有写入（包括 START/ACK）忽略并置 ERROR。
ACK_DONE 在非 BUSY 时清 DONE、ERROR；同时 START/ACK 时 START 优先。非法 MULT/SHIFT 保留旧配置并置 ERROR，合法配置写不清 ERROR。
DONE 保持到 ACK/START/复位；ACK 保留输出。CLASS_ID、结果和周期复位为零；新启动清结果和周期，BUSY 期间输出未完整，不可使用。
单次 CYCLE_COUNT=39，双次为 59；接受 START 后计数，到整批结果完成，不含软件传输。双次共享权重/偏置/量化，均完成才 DONE。未定义读零，非 BUSY 时未定义/只读地址写忽略，CONTROL 读零。

## 数据窗口

偏移相对基址；区间右端不包含。四个 INT8 打包一个 32 位字。

| 内容 | 起始 | 大小（字节） | 结束 |
| --- | --- | ---: | --- |
| INPUT[64] | 0x0040 | 64 | 0x0080 |
| W1[32][64] | 0x0100 | 2048 | 0x0900 |
| W2[6][32] | 0x0900 | 192 | 0x09C0 |
| B1[32] | 0x09C0 | 128 | 0x0A40 |
| B2[6] | 0x0A40 | 24 | 0x0A58 |
| HIDDEN[32]，调试只读 | 0x0A80 | 32 | 0x0AA0 |
| SCORE[6]，只读 | 0x0B00 | 24 | 0x0B18 |
| INPUT1[64] | 0x0C00 | 64 | 0x0C40 |
| HIDDEN1[32]，只读 | 0x0C40 | 32 | 0x0C60 |
| SCORE1[6]，只读 | 0x0C80 | 24 | 0x0C98 |
| CLASS_ID1，只读 | 0x0C98 | 4 | 0x0C9C |

权重按输出神经元优先排列：W1[j][i] 连续 i；W2[k][j] 连续 j。
低地址元素放 word[7:0]，后续元素放 [15:8]、[23:16]、[31:24]。
偏置/得分每元素一 word，读取按 INT32 有符号解释；配置和状态按无符号解释。

## 桥接时序

使用保留的 axi2mem：
- 本地地址是 word 地址，软件地址是 byte 地址，转换要明确。
- 写仅在有效请求和写使能同时成立时发生。
- 读按桥接约定在下一拍有效；保持读请求不能造成副作用。
- 当前 NPU 包装层不传递 byte enable，软件使用完整 32 位写。
- 外围 addr[13:2] 截断造成 16 KB 地址别名，保持外围不变；软件只用基址加合法偏移。大译码区间不代表实际容量。
- 若最终存储宏延迟不同，需要显式适配；不能直接更改读延迟而保留旧桥接契约。

## 软件执行

初始化配置→装载权重/偏置→写输入→START→带超时轮询 DONE→读得分/类别→ACK_DONE。
不得用未完成结果做分类；状态行为和内存数据有效期由测试覆盖。

双次：装共享参数、INPUT/INPUT1→BATCH_COUNT=2→START→轮询 DONE→读两份结果/计数→ACK。之后恢复 BATCH_COUNT=1 继续单次。BUSY 时所有写拒绝并置 ERROR。
权重为同步 bank 存储，外围读仍下一拍；RAM 阵列不复位，以有效位屏蔽旧值，复位后重新装载模型。

## DMA 装载

0x0D00–0x0D1F 为独立 DMA CSR，源地址/目的地址使用 byte，长度使用 32-bit word。原控制和数据窗口不变。完整协议及错误行为见 [DMA](dma.md)。
