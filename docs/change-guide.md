# 修改边界与验证操作指南

适用版本：Lab 3 固定外围 + HAR V1；2026-10-08。
读完本页应能确定：要改哪一个文件、哪些接口必须保留、新增文件如何加入编译、修改后怎样判定通过。

## 1. platform 和 rtl 如何连接

```text
platform/course_soc/soc/rtl/my_soc_top.sv
    ├── CPU、AXI、Debug、Boot RAM、主 SRAM
    └── my_npu_subsystem.sv        固定总线桥、地址转换与握手
            └── simple_npu_top    在 rtl/npu 中选择一份
                    └── NPU 核心与本地数据存储
```

platform 是选定的课程底座，里面也有 RTL；根目录 rtl 是团队自主开发区域。
当前没有第二份系统顶层。lab3/har 两份 NPU 是替代关系，不是两个同时连接的加速器。

## 2. 我们能改什么

| 位置 | 是否改 | 怎样改 |
| --- | --- | --- |
| [rtl/npu/har/har_npu_core.sv](../rtl/npu/har/har_npu_core.sv) | 主要开发区 | 修改 MAC 数量、调度、流水线、点积、ReLU/量化、Argmax 的内部实现；保留约定的数值和状态语义 |
| [rtl/npu/har/simple_npu_top.sv](../rtl/npu/har/simple_npu_top.sv) | 可以改内部实现 | 调整寄存器组织、本地存储、读写实现；对固定外围的端口和读延迟保持一致 |
| [rtl/memory/](../rtl/memory/README.md) | 可新增 | 从 NPU 中拆出输入、权重、中间结果存储；加入编译清单并验证延迟/复位/装载 |
| [rtl/npu/lab3/](../rtl/npu/lab3/) | 兼容维护区 | 修复原回归配置的实现问题，保留原 4 位、4×4 运算和地址行为；HAR 新功能放 har/ |
| [model/](../model/README.md) | 可以改 | 训练、量化和导出真实模型；参考算法只能随明确的规格变更调整，不能跟着错误 RTL 改答案 |
| [verification/npu/](../verification/npu/README.md)、[verification/mmio/](../verification/mmio/README.md)、[verification/soc/](../verification/soc/README.md) | 可新增/改进 | 增加 HAR 用例、边界、失败回归；保持独立参考和有效断言 |
| [scripts/](../scripts/README.md)、[sw/](../sw/README.md) | 可以改 | 添加编译源、运行入口、C 驱动和自检；使用当前数值/MMIO 契约 |
| [docs/](README.md)、[configs/](../configs/README.md)、[reports/](../reports/README.md) | 可以改 | 与实际实现同步，记录新的验证版本及限制 |
| [platform/course_soc/](../platform/course_soc/README.md) | 当前冻结 | CPU、AXI、Debug、启动、复位、主 SRAM、系统顶层、NPU 接入桥均保持原字节 |
| [verification/lab3/](../verification/lab3/)、[sw/startup/lab3/](../sw/startup/lab3/)、[filelists/lab3_original.f](../filelists/lab3_original.f) | 当前冻结 | 原课程 TB、C、hex、启动/链接、源清单用于回归，不改原测试和期望 |
| platform/course_soc/manifest.json | 基线记录 | 不通过重写 SHA 来让未经讨论的外围改动“通过” |

rtl/soc/ 当前只有说明，未参与构建，不是另一个允许随意改外围的入口。
如确实发现外围缺陷，先记录问题、影响和最小修复方案，由团队明确决定解除对应冻结点，再用单独 PR 更新来源/校验并重跑全系统回归。当前普通 NPU 开发不走这条路径。

## 3. 不变的外部契约

HAR 可以更换内部结构，但连接固定外围时必须保持：

| 项目 | 当前约定 |
| --- | --- |
| 模块名 | simple_npu_top |
| 端口 | clka、rst_ni、ena、wea、addra[11:0]、dina[31:0]、douta[31:0] |
| 复位 | rst_ni 低有效，输出/状态按当前契约复位 |
| 写请求 | ena && wea；软件完整 32 位对齐写，桥没有向 NPU 传递字节使能 |
| 读请求 | ena && !wea；douta 下一拍有效，状态读无副作用 |
| 地址 | 基址 0x70000000，外围用 addr[13:2] 产生 word 地址；NPU 本地 16 KB |
| HAR 数据/寄存器 | 按 [mmio.md](mmio.md) 的偏移、字节排列、状态和错误行为 |
| 算术 | 按 [numerics.md](numerics.md)：INT8 输入/权重、INT32 合法累加、隐藏 0–127、同尺度有符号得分、平局取最小下标 |

第一层/第二层内部接口可以随重构调整，但要同步包装层和自主 TB。
修改 MMIO、舍入、位宽、零点或标签映射属于规格变更，需要先写清旧/新行为，再同步参考、导出、软件、文档和测试；不能只改一个 RTL 文件。

## 4. 怎样开始修改

1. 一次任务明确一个目标，例如“把一个 MAC 改为四个，保持逐值结果与 MMIO 行为”。
2. 从包含已验证基线的版本建立任务分支。当前基线在 PR #1 的 codex/lab3-platform-npu，尚未合入 main；合并前以该分支为起点，合并后以更新的 origin/main 为起点。
3. 先修改 har/ 内部；新增模块时同时处理下面的编译入口。
4. 给缺陷补能重现的 HAR 测试，保留失败向量；优化保留同一整数参考作为对照。
5. 先小规模调试，完整回归通过后记录结果并提交 PR；由另一名成员复核后合并。

合并前建立新任务分支的示例（将名字换成自己的任务）：

```text
git fetch origin
git switch -c codex/npu-your-task origin/codex/lab3-platform-npu
```

### 新增模块必须加入哪些地方

目前真正的源列表在 [scripts/run_tests.py](../scripts/run_tests.py)，不是在空目录 README 中，也不是在生成的 build/*.f 中。

例如增加 rtl/npu/har/har_mac.sv：

- units()：把依赖文件加入 har_core 与 har_mmio 各自的 sources 列表，按依赖顺序放置。
- filelist(profile)：把文件加入 har 配置的 sources 列表；该列表会生成 SoC 的 build/har.f。
- 新文件如果在 rtl/memory/，调整路径生成逻辑以包含它，不把它伪装为 har/ 内的文件。
- lab3 配置继续编译自己的 PE/core/top；不要同时编译两份 simple_npu_top。
- 不直接改 build/har.f：下次运行会重新生成。不修改冻结的 lab3_original.f。

仅创建文件而不更新上述入口，不等于新模块已被验证。

### 优化周期和存储时特别注意

当前 2279 周期的断言出现在核级 TB、MMIO TB 和 scripts/build_har_firmware.py。
增加并行度或流水线后，先推导新的计算周期和计数边界，再同步这些自主断言、数值/MMIO 文档和报告；同时逐值比较结果。不能只删除周期断言。

存储从寄存器改为同步 RAM 后，核内可能需要等待读数据；对外围仍要兑现下一拍读出。要验证读后写、权重复用、连续推理和复位中止。主 SRAM 的 8 KB 不因 NPU 存储优化而增加。仿真正确不证明新存储已映射到目标宏或 FPGA RAM。

## 5. 改完怎样验证

在仓库根目录执行，工具安装/许可证见 [environment.md](environment.md)。

### 第一步：结构与冻结边界

```text
python scripts/check_repo.py
python scripts/check_platform.py
```

前者验证目录、Markdown 链接、配置和 MMIO 窗口；后者验证 90 个导入文件原字节。
两者 PASS 只代表结构/边界正确，不代表 NPU 算法正确。
SHA 不符时查看是否误改、格式化或转换了外围行尾；不要直接重生成 manifest 掩盖问题。

### 第二步：本地快速调试

```text
python scripts/run_tests.py --unit --count 12
```

使用 Icarus，运行原 Lab 3 核级/MMIO 以及 HAR 核级/MMIO。--count 控制 HAR 核例数量；HAR MMIO 当前固定 12 组。
这一步适合修改过程，不代替提交前的 1000 组回归。

### 第三步：完整计算与 MMIO 回归

```text
python scripts/run_tests.py --unit
```

默认 HAR 核级 1000 组，逐项比较 32 hidden、6 score、class，并覆盖复位、忙时启动、DONE 保持、ACK。
MMIO 覆盖打包/读回、忙时写拒绝、非法配置、状态读和复位；原兼容核/MMIO 也必须通过。

### 第四步：真实 CPU + 全系统回归

```text
python scripts/run_tests.py --soc --vsim "本机 vsim 可执行文件路径"
```

运行原 test1/test2/test3/hand 四镜像，以及 HAR 的真实 CV32E40P 六次连续推理。
检查 CPU 写入的 SRAM PASS magic=c0dec0de，HAR 程序逐项核对 hidden/score/class/计算周期。FAIL、TIMEOUT、缺失标志或编译错误均不通过。

原四镜像验证 lab3 兼容配置，HAR 镜像验证 har 配置；只通过旧矩阵乘不能证明新 MLP 正确。只通过核级也不能证明 AXI/CPU 数据传输正确。

Icarus/vvp 未在 PATH 时使用 --iverilog/--vvp。可以用一个命令运行两套：
python scripts/run_tests.py --vsim "本机路径"。
Windows 可执行文件路径带空格时保留引号。

## 6. 不同修改的最低验证要求

| 修改 | 提交/合并前要求 |
| --- | --- |
| 只改说明文档 | check_repo + check_platform；无需重跑未改的硬件 |
| HAR core/MAC/流水线/存储/控制 | check_repo + check_platform + 完整 --unit + --soc |
| HAR top/MMIO/状态/地址 | 同上，增加针对新行为的接口用例 |
| 兼容 lab3 实现 | 同上，确保原四镜像仍通过 |
| 新增 RTL 文件或修改编译入口 | 同上，确认单元与 SoC 都实际编译了新文件 |
| 修改参考、向量、生成器、软件镜像 | 完整 --unit + --soc，加独立数值/编码依据，保留原回归 |
| 改训练模型但契约保持 | 先整数参考与准确率评估，再增加真实样本的 RTL/SoC 对照；当前脚本默认只验证合成向量 |
| 修改 FPGA/ASIC 存储适配 | RTL/SoC 回归之外，运行对应综合/实现/板级或签核检查；当前仓库尚无这些流程的 PASS |

GitHub CI 自动运行结构、外围 SHA 和 Icarus 回归。当前 CI 没有 ModelSim，绿色 CI 不能代替本机 --soc，更不能代替 FPGA/ASIC 证据。

## 7. 哪里看结果，失败怎样定位

- build/logs/har_core.log：算法/中间值、控制或周期。
- build/logs/har_mmio.log：字节排列、寄存器、忙时/错误状态、读延迟。
- build/logs/har_soc_6_classes.log：CPU/总线到 NPU 的端到端行为。
- build/logs/lab3_soc_lab3_test*.log、lab3_soc_lab3_hand.log：旧配置回归。
- build/results/unit.json、soc.json、all.json：分别由对应运行模式生成；每条应有 pass_=true，结果必须包含预期测试且命令成功结束。

先看第一个失败和实际编译源，不连续修改多个层级猜原因。
核例失败先比较 hidden/score；MMIO 失败先检查 byte/word 地址和打包；SoC 失败先检查镜像是否装载、CPU 是否启动，再检查 MMIO。SoC $finish 返回零仍可能是 FAIL，运行脚本会检查真实标志。

build 不提交。新的报告写明被验证代码 commit、命令、工具、种子/模型 SHA、测试数量、PASS/FAIL、计算与端到端周期及未验证范围。原 reports/baseline.* 记录初始基线，不自动代表以后改动；新增版本报告，不复用旧 PASS 冒充新结果。

## 8. 完成一个 NPU 修改的标准

外围 SHA 一致；计算/状态/接口契约满足；1000 组核例、MMIO、原四镜像、HAR CPU 测试通过；新功能有针对性覆盖；文档与编译入口同步；提供当前代码证据和团队复核。

当前合成权重只证明计算与集成正确。正式 HAR 还需要真实特征、训练权重和准确率验证，物理交付还需要 FPGA 与 ASIC 流程。
