# 顺序任务 ABI v1

本接口用于新增任务引擎，旧 MMIO、MODE0/1/3 地址和语义保留。此文档冻结软件协议，**不表示硬件已经实现或通过验证**；实现状态以 report/npu_task_engine_20261117/state.json 为准。

CPU 将只读任务表放在现有 8KiB SRAM，配置 BASE/COUNT 后 START 一次。每条 FC 描述符对应 K≤64、N≤32、batch≤4 的计算块；64B 权重 tile 的循环、复用与预取仍在硬件内。沿 K 的块必须连续执行，同一 context、N、batch，首块 INIT，其后续算，末块 LAST_K。中途不量化。ACTIVATION 描述符处理已经量化的 INT8，支持需要保留独立舍入边界的连续激活。

## 表和描述符

小端，表首地址按 64B 对齐，COUNT=1..128，表的全部字节必须在 [0x80000000,0x80002000)。每条 64B，16 个字：

| 字 | 内容 |
| --- | --- |
| 0 | [7:0]版本1；[11:8] OP；[15:12] ACT；16 INIT；17 LAST_K；18 INPUT_INTERNAL；19 KEEP_OUTPUT；20 END；21 LUT_CACHE；其他0 |
| 1 | [7:0]K；[15:8]N；[23:16]batch；其余0 |
| 2..5 | input、weights、bias、output 地址 |
| 6 | [15:0]input row stride，[31:16]output row stride，单位字节 |
| 7 | 有符号32位 FC multiplier |
| 8 | [7:0]FC shift，[15:8]activation shift，[23:16]negative shift；其余0 |
| 9..10 | 有符号32位 activation multiplier、negative multiplier |
| 11 | 256B LUT 地址，非 LUT 模式为0 |
| 12 | ReLU6 的 INT8 上限，0..127；高位0 |
| 13 | context，32位不透明标识 |
| 14..15 | 保留，必须0 |

OP：FC=1、ACTIVATION=2。ACT：NONE=0、ReLU=1、ReLU6=2、LeakyReLU=3、Sigmoid=4、Tanh=5。END 当且仅当当前条为 COUNT 中最后一条，不能提前结束或跳转。未知版本/OP/ACT 明确报错。

SRAM 张量按行存储，行首和 stride 按4B对齐，stride≥向上取整到4B的逻辑行宽。范围检查包含最后一个完整总线字。权重布局沿用 compiler/tiling.py：K 每2个输入一组，N 每8个输出一组，每组16B，尾部补0。权重大小 ceil(K/2)×ceil(N/8)×16B。bias 是 N 个符号扩展的 INT22、每项一个32位字。INIT=0 时 bias 地址必须0。LAST_K=0 时 output/stride 必须0，不得 KEEP/END/激活。

INPUT_INTERNAL 要求 source/stride=0、每样本宽≤32，且上一条发布了形状匹配的 KEEP_OUTPUT。一次内部输入消费该 buffer 的有效标记。KEEP_OUTPUT 要求 destination/stride=0，保留 batch×N 个字节。写 SRAM 的输出撤销内部标记。跨执行段不保留内部输入或部分和的有效性。编译器仅在旧输入不再使用时选择内部交接；多个 N 块、多个消费者、CPU 交接等场景使用 SRAM。

ACTIVATION 要求 K=0、weights=bias=0、INIT=0、LAST_K=1、FC multiplier/shift=0，N 是输入/输出宽。普通输入从 SRAM 或有效内部输出读取。不得用 ACT 任务打断部分和链。

## 整数规则

INT22 部分和范围 [-2097152,2097151]，编译器必须证明所有允许输入均不溢出；不安全的 Linear 使用已有 CPU INT32 路径。硬件对搬入的 bias 检查符号扩展。缩放使用精确宽乘积（INT22×INT32 至少54位），shift=0..24：

`Q(v,m,s)=sat_int8(s==0 ? v*m : arithmetic_shift_right(v*m+2^(s-1),s))`

这是最近舍入，恰好半值向正无穷；例如 Q(-3,1,1)=-1。FC LAST_K 先执行 Q(acc,fc_m,fc_s)，产生 INT8，再执行 activation。融合不得删去这个饱和/舍入边界。

| ACT | 在上述 INT8 q 上执行 |
| --- | --- |
| NONE | Q(q,act_m,act_s)，普通恒等参数为1/0 |
| ReLU | Q(max(q,0),act_m,act_s) |
| ReLU6 | min(Q(max(q,0),act_m,act_s),clamp_max) |
| LeakyReLU | q<0 时 Q(q,negative_m,negative_s)，否则 Q(q,act_m,act_s) |
| Sigmoid/Tanh | 返回 LUT[q+128]，表项为有符号 INT8 |

LUT 表地址按4B对齐，256B全部在 SRAM 内。直接访问路径先实现；LUT_CACHE 仅当 CAPABILITIES 宣告支持时允许。缓存方案的面积/访问代价尚未测量，不默认启用。

## 寄存器

基地址 0x70001600，以下均为32位；未定义写入拒绝，保留字段读0。新增内部窗口只允许当前任务引擎拥有的 DMA 访问：0x1640..167f 描述符入口、0x1680..16ff 打包输出、0x1700 LUT 字入口（地址均以0x70000000为基）。CPU 不得直接写这些入口。

| 偏移 | 名称 | 语义 |
| --- | --- | --- |
| 00 | CONTROL | 写1 START，写2 ACK；不能同时置位 |
| 04 | STATUS | bit0 DONE、1 BUSY、2 FAILED、3 OUTPUT_VALID、4 REJECTED |
| 08 | BASE | 任务表地址，仅空闲可写 |
| 0c | COUNT | 任务数，仅空闲可写 |
| 10 | CAPABILITIES | [31:24]ABI，[23:16]Kmax，[15:8]Nmax，[5:0]ACT支持位，[6]LUT缓存，[7]内部交接 |
| 14 | INDEX | 当前/失败描述符下标，从0起 |
| 18 | ERROR | 已接受执行段的终止错误 |
| 1c | CYCLES | 此执行段 BUSY 拍数 |
| 20 | COMPLETED | 已完整提交的描述符数，LAST_K=0 的计算完成也计数 |
| 24 | REJECT_CODE | 未接受控制请求的错误，不中止当前执行段 |

错误码：0正常、1忙、2对齐、3范围、4描述符格式、5部分和/内部数据上下文、6 DMA/AXI失败、7数值/尺寸、8不支持。已接受的执行段失败时 DONE=1、FAILED=1、OUTPUT_VALID=0，停止启动后续任务，等待已发出的 AXI 事务完成后退出。非法 START 配置直接终止且不发 DMA。忙时 START/ACK/配置写入及旧配置写入都被拒绝，不能修改活动配置、输出或中止已接受的事务；设置独立 REJECTED/REJECT_CODE。旧专用运算忙时也不能启动新执行段。

空闲 ACK 清除完成、错误、拒绝及输出有效标志。START 清除旧完成及全部内部有效上下文。复位清除控制、有效性及任务进度，须遵守 SoC 原有系统复位与 AXI 清空协议；不能仅复位局部状态后遗留 AXI 事务。DMA 错误不回滚已写 SRAM 的字节，软件重建相应输出。

每个 SRAM 输出的最后字使用字节 WSTRB，不能覆盖 padding/相邻张量；每行的 AXI B 成功返回后才完成该行，全部行成功才提交当前任务。全部任务完成后才置最终 OUTPUT_VALID/DONE。KEEP 也只在完整后处理成功后发布。失败撤销当前输出、部分和和内部交接有效性；COMPLETED 之前的 SRAM 字节可能仍存在，不能把它当作整段成功。

执行期间 CPU/Debug 不得修改任务表、输入、权重、bias、LUT 或目标输出；CPU 也不应运行会与这些地址冲突的代码。硬件防止输出覆盖整个任务表；其他图级存活期、代码和常量重叠由编译器布局检查。硬件不会扫描整张未来任务表来证明所有别名关系。

CPU 使用普通 RV32 MMIO 和 fence，不新增 CPU 自定义指令。runtime/har_task.h 给出结构与非阻塞启动/轮询接口；有限次数轮询超时并不取消 AXI，复用相关内存前需要系统复位。

## 软件协议验证

`python test/int8/test_task_abi.py`：独立的16字线格式向量、版本/保留位/地址/范围/COUNT/END/上下文拒绝、内部标记生命周期、全部256种输入的六种激活、INT22和INT32系数边界/负数舍入，以及两次量化不能合并的反例。后续必须用相同向量验证 RTL 解码和完整 SoC，主机 codec 通过不能替代硬件验收。
