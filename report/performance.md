# SoC 与 NPU 优化报告

## 2026-11-09 第四轮：八字加载调度与地址复用

默认固件改为 **reuse8**：每轮处理八个字，先发出独立加载，再写入或比较；已知地址优先用一次 `addi` 调整，避免重复构造完整地址。对照基线是上一轮 `11d69dd` 的 `scheduled4`，CPU/NPU/总线 RTL、模型和输入不变。

38 组相同任务的完整 SoC 自检合计 **82977→79949 拍，减少 3.65%**；首条取指到真实 NPU DONE 合计 **63913→63126 拍，减少 1.23%**。38 组的两种计时口径均无退步。这些是本次任务集的测量，不代表任意程序都能获得相同比例的收益。

### 修改及取舍

四字搬运循环处理八个字需要两轮，循环主体共 24 条指令；八字循环一轮共 20 条。独立加载提前发出，使后续使用数据时更少等待。比较循环使用两组互不重叠的寄存器保存实际值和 golden 值。六字偏置、六字分数和单字分类结果仍按实际长度处理，不越界读取。

生成器在构建程序时跟踪 x5/x6 已知指针值：相邻区间用小偏移更新，靠近 NPU 基址的地址从固定 x20 计算；跨越 START/状态轮询后清除跟踪，重新建立地址。运行时没有新增地址预测硬件，也没有新增指令集。仍只使用 RV32I。

以下训练用例 seed 10000 均在原 `tb_soc.sv` 上运行，代码大小只算程序区：

| 候选 | 程序字节数 | 完整自检拍数 |
| --- | ---: | ---: |
| scheduled4 | 1388 | 2810 |
| aligned4 | 1604 | 2796 |
| poll4 | 1404 | 2819 |
| poll8 | 1420 | 2826 |
| poll_eq | 1388 | 2812 |
| reuse4 | 1224 | 2788 |
| reuse_eq | 1224 | 2795 |
| scheduled8 | 1660 | 2723 |
| reuse8 | 1520 | 2692 |
| reuse8_eq | 1520 | 2699 |

循环对齐在部分输入上退步；延长轮询间隔没有稳定收益；单独复用地址虽然缩小程序，也可能因取指与总线访问时序改变而变慢。最终采用八字调度与地址复用的组合。精简 busy 判断的 `reuse8_eq` 在训练用例中反而多七拍，因此没有设为默认。选择依靠实测拍数，不只看静态指令数量。

### 区分完整自检与结果产生时间

| seed / batch | 完整自检拍数 | 减少 | 首 fetch→NPU DONE | 减少 |
| --- | ---: | ---: | ---: | ---: |
| 0 / 4 | 2901→2737 | 5.65% | 2112→2051 | 2.89% |
| 1 / 2 | 2043→1977 | 3.23% | 1607→1591 | 1.00% |
| 2 / 1 | 1634→1600 | 2.08% | 1367→1357 | 0.73% |
| 10000 / 4 | 2810→2692 | 4.20% | 2027→2009 | 0.89% |

| 训练 seed 10000 的阶段或事件 | scheduled4 | reuse8 |
| --- | ---: | ---: |
| 首条取指→NPU START | 1087 | 1065 |
| NPU START→DONE | 940 | 944 |
| DONE→成功写回 | 777 | 677 |
| minstret 指令计数事件 | 809 | 690 |
| load-use 相关事件 | 77 | 69 |
| 取指等待周期 | 105 | 51 |

训练用例完整程序少 118 拍，主要是结果检查阶段少 100 拍，启动前少 22 拍，而 NPU START→DONE 多了 4 拍。真正到 NPU 结果产生仅快约 0.89%，不能把 4.20% 写成 NPU 算力提升。FC1/FC2 发射周期仍为 256/64，MAC 运算量没有减少。训练用例 load/store 事件仍为 287/113；部分随机用例会因轮询次数变化增加一次状态读取。

旁挂监测器不驱动 DUT 信号，全部功能字段与原 testbench 对应结果相同，START→DONE 与硬件计数器相等。三阶段之和是首 fetch→成功写回，比原 testbench 的完整窗口固定少六拍。load-use 事件数表示相关事件次数，不等于全部停顿拍数。[完整对照](loop_optimization_20261109/final_extended/results.json)、[真实阶段计时](loop_optimization_20261109/final_profile/results.json)。

### 验证与交付

- 最终四个候选×38 组输入全部通过原完整 SoC RTL 自检；选定版与基线的 76 次阶段监测全部匹配。此前候选筛选日志一并保留。
- 三个负例分别翻转最后样本的隐藏层、分数、分类 golden 尾字，真实 CPU 均走数值失败路径。所有结果检查和统计没有省略。[负例](loop_optimization_20261109/final_faults/results.json)。
- SRAM 写压力和代码别名修改两个兼容程序通过；它们是兼容负载，不应混入普通 HAR 延迟。[兼容测试](loop_optimization_20261109/final_workloads/results.json)。
- 同 seed 的模型、输入、参数和 golden 数据一致，原 scheduled4 镜像与前轮归档一致。最终 38 份活动镜像与实测 reuse8 逐字匹配；现有八个完整二进制同步更新。生成模式、代码大小、数据边界及 SHA 均有记录。[镜像核对](loop_optimization_20261109/final_images.json)、[独立证据核对](loop_optimization_20261109/audit.json)。
- 最大程序 1524 B，较基线最大 1392 B 增加 132 B，仍低于全部用例的首权重地址（最早 4092 B）。使用既有 SRAM 空间，没有增加芯片硬件面积；2×2 mm 裸片限制继续保留。活动 FPGA 文件已更新，历史 versions 和既有板测记录不变。

本轮仅修改固件生成和测量入口，**没有新增综合、PNR、SDF 后仿或上板结果**。此前硬件面积与时序结论沿用其原有验证边界；10 ns RTL 仿真时钟不证明物理频率。

复现最终候选与基线时，加载 Xcelium 环境，并使用新的输出目录；`--seed` 可重复指定 0～31 和 10000～10005：

```bash
python3 test/int8/run_firmware_bench.py --baseline-mode scheduled4 \
  --mode scheduled4 --mode reuse8 --out test/int8/runs/loop_recheck
python3 test/int8/run_firmware_profile.py --bench test/int8/runs/loop_recheck \
  --mode scheduled4 --mode reuse8 --out test/int8/runs/loop_profile_recheck
python3 test/int8/run_firmware_faults.py --benchmark test/int8/runs/loop_recheck \
  --mode reuse8 --out test/int8/runs/loop_fault_recheck
python3 tools/project.py check
```

后续若要显著减少推理延迟，应继续分析 NPU 的数据搬运与计算重叠。把输入和偏置也交给 DMA 是候选方向，但当前 DMA 只接受权重 bank 目的窗口，需要修改目的地址白名单和 NPU 写入权限并重新验证，本轮没有实现。只读审查另发现 INPUT2 MMIO 窗口放行了 64 字，而 x 数组对应剩余两个样本仅需 32 字；当前合法固件只使用前 32 字，越界地址处理需要另做定向测试与修复，不作为本轮已验证成果。

[本轮 SHA 与结果索引](loop_optimization_20261109/summary.json)。

---

## 2026-11-09 第三轮：CPU 固件指令与拍数优化

本轮保持 `f5e3a7c` 的 CPU、NPU、缓存和总线 RTL 不变，优化 CPU 实际执行的 RV32I 程序。默认固件现为 **scheduled4：紧凑常量加载、四字循环展开、独立加载提前调度**。38 组相同任务的完整 SoC 自检总计 **99698→82977 拍，减少 16.77%**；6 组训练数据每组都是 **3462→2810 拍，减少 18.83%**。这次是软件指令序列优化，没有新增 CPU 指令、MAC 或 bank，也没有新增硬件面积。

### 改了什么

原搬运循环每传一个 32 位字执行六条指令：读、写、更新两个地址、更新计数、循环跳转。现在一轮搬四个字，只更新一次地址和计数，四个字的循环主体由 24 条降至 12 条。六字偏置、六字分数和单字分类结果分别处理尾部，不越界访问。常数能用一条 `addi` 或 `lui` 表达时不再固定生成两条指令；地址标签修补仍保留两条，避免覆盖后续指令。

同一组内先读四个互不依赖的数据，再逐个写入或比较，给加载返回留出时间。所有隐藏层、六类分数、分类结果、FC1/FC2 计数和权重 tile 计数检查保留。CPU 仍执行完整的加载、NPU 启动、等待、逐字结果校验和统计写回。

这就是本轮“优化 CPU 指令”的含义：改变既有指令的数量和顺序。当前核支持 RV32IMC，但固件仍只用 RV32I；`COREV_PULP=0`，硬件循环及 PULP 扩展未启用，不能直接插入这些扩展指令。RVC 压缩指令尚未采用。

### 同一硬件、同一任务对照

所有模式使用原始 `tb_soc.sv`、同一个 Xcelium 编译快照和 10 ns 功能仿真时钟。每个 seed 的权重、输入、参数和 golden 数据逐字节相同，只有程序区不同。数据比较覆盖部分边界用例从 `0xffc` 开始的首个权重字，代码上限也按实际首权重地址检查。

| 训练 seed 10000，batch 4 | 程序字节数 | 完整自检拍数 |
| --- | ---: | ---: |
| 原始指令序列 baseline | 1140 | 3462 |
| 仅精简常量 compact | 1024 | 3446 |
| 两字展开 unroll2 | 1088 | 3111 |
| 四字展开 unroll4 | 1388 | 2904 |
| 八字展开 unroll8 | 1660 | 2833 |
| **四字展开并调度 scheduled4** | **1388** | **2810** |

| 用例 | baseline | scheduled4 | 减少 |
| --- | ---: | ---: | ---: |
| seed 0，batch 4 | 3471 | 2901 | 16.42% |
| seed 1，batch 2 | 2432 | 2043 | 15.995% |
| seed 2，batch 1 | 1919 | 1634 | 14.85% |
| 训练 seed 10000，batch 4 | 3462 | 2810 | 18.83% |
| 32 随机 + 6 训练任务合计 | 99698 | 82977 | 16.77% |

38 组逐例减少 14.03%～18.83%。八字展开合计 83100 拍，与所选方案非常接近；其 32 组随机任务合计还少 15 拍，但六组训练任务各多 23 拍。所选四字方案最大程序 1392 B，小于八字方案的 1664 B，均在现有 4 KiB 程序区内。选择兼顾了拍数和代码空间，不代表它对任意未来程序都最优。[六模式筛选](firmware_optimization_20261109/sweep/results.json)、[38 组扩展对照](firmware_optimization_20261109/extended/results.json)。

### 加速发生在哪里

只读监测器旁挂原 testbench，观察真实的首条固件取指、NPU START/DONE、成功结果写回。12 个监测用例的全部七项功能结果都与原 testbench 相同；START→DONE 的间隔也逐例等于 NPU 硬件计数器。

| 训练 seed 10000 的阶段或事件 | baseline | scheduled4 | 变化 |
| --- | ---: | ---: | ---: |
| 首条取指→NPU START：配置与搬运 | 1437 拍 | 1087 拍 | 少 350 拍 |
| NPU START→DONE | 944 拍 | 940 拍 | 少 4 拍 |
| DONE→成功写回：轮询收尾、全部校验及统计 | 1075 拍 | 777 拍 | 少 298 拍 |
| **首条取指→NPU DONE，含搬运、不含结果读回** | **2381 拍** | **2027 拍** | **少 14.87%** |
| 架构 minstret 指令计数事件 | 1367 | 809 | 少 40.82% |
| load-use 相关事件 | 224 | 77 | 减少加载依赖 |
| CPU load / store 事件 | 287 / 113 | 287 / 113 | 相同 |
| FC1 / FC2 MAC 发射周期 | 256 / 64 | 256 / 64 | 相同 |

因此，完整自检少 18.83% 不能表述为 NPU 计算快了 18.83%。真正到 NPU 结果产生的路径少 14.87%，主要来自 CPU 配置与搬运；NPU 自身只少四拍，反映同一总线上访问时序的变化，算术工作量没有减少。

`minstret_events` 来自 CV32E40P 既有架构事件，不是取指请求数；核心在合法 ID 发射处实现该事件并提供 CSR 退休计数语义。计数窗口截至成功字写入 SRAM，并非程序无限 halt 循环。load-use 数是相关事件次数，不能直接当作全部停顿拍数，也不能与其他事件相加作为总周期。被动监测的首 fetch→成功写回窗口比原 testbench 固定少六拍，各表保持自己的计时边界。[原始监测证据](firmware_optimization_20261109/profile/results.json)。

八字展开的指令事件只有 725，比 scheduled4 的 809 更少，但 load-use 事件为 227，最终仍多 23 拍。反过来，scheduled4 的取指等待事件从 baseline 的 10 增至 105，体现代码展开给 128 B 指令缓存带来的成本。因此选择依据实际拍数，而不是只数指令。

### 验证、交付与限制

- 六模式×四个 seed 的 24 次筛选、三模式×38 个 seed 的 114 次扩展，全部在真实 CPU 执行下通过完整 SoC RTL 自检；各模式的 FC1/FC2 发射周期相同。
- 12 次只读性能监测通过，原功能结果不变。额外 SRAM 写循环及代码别名修改两个兼容程序也通过，分别为 3844 和 3063 拍；它们不是普通 HAR 延迟。
- 故意翻转最后一个样本的隐藏层尾字、分数尾字、分类 golden，三次都由真实 CPU 走失败路径，原 testbench 报 `CPU numerical self-check failed`，证明这些校验没有被优化掉。[负例](firmware_optimization_20261109/faults/results.json)。
- 228 份生成镜像的数据区一致，38 份 baseline 的 HEX 和汇编与修改前逐字节一致。选定默认后，38 份默认程序又与已测 scheduled4 镜像一致；常量、地址修补及分支边界检查通过。[生成器检查](firmware_optimization_20261109/generator_validation.json)。
- 活动 FPGA 固件镜像同步使用所选程序，并保留模式、代码大小与哈希。历史冻结目录和板测记录保留；本轮没有重新板测。

复现时先加载 Xcelium 环境，再运行以下入口；输出目录必须是新目录：

```bash
python3 test/int8/run_firmware_bench.py --out test/int8/runs/fw_sweep_new
python3 test/int8/run_firmware_profile.py --bench test/int8/runs/fw_sweep_new \
  --out test/int8/runs/fw_profile_new --mode baseline --mode scheduled4 --mode unroll8
python3 test/int8/run_firmware_faults.py --benchmark test/int8/runs/fw_sweep_new \
  --mode scheduled4 --seed 10000 --out test/int8/runs/fw_faults_new
python3 fpga/firmware/generate_images.py
python3 tools/project.py check
```

本轮没有修改硬件，未重跑综合、PNR 或 SDF 后仿。上轮所选 RTL 的综合单元面积仍可作为该硬件的参考：2.148261 mm²（含 SRAM），计划含 IO 裸片 1.948×1.948 mm；这不是新的物理实现结果，也没有新增流片签核结论。10 ns 功能时钟不能证明物理上可跑 100 MHz。

下一轮若继续减少软件拍数，优先实测 RVC 压缩编码、热循环对齐和轮询调度，关注代码增大造成的取指压力。若要缩短 NPU 自身的约 940 拍，则需另行分析 DMA/计算重叠；单纯精简 CPU 指令不会减少相同网络的 MAC 运算量。

[本轮证据总索引](firmware_optimization_20261109/summary.json)。

---

## 2026-11-09 第二轮：缓存一致性、DMA 响应和面积优化

上一版 `49911b2` 已推送到 GitHub `rtl-dev`。本轮在独立 `codex/rtl-dev-opt-20261109` 分支实验，保持 32 个共享乘法器、两组 64 B 权重 bank、128 B 指令缓存以及 `CUT_SLV_AX`。标准 HAR 自检的改进为 **1.37%～2.49%**；额外 SRAM 写入负载的改进为 **41.96%**，二者对应不同工作负载。

### 修改及取舍

- **按 SRAM 物理地址失效指令缓存。** 普通数据写入保留无关指令行；命中指令行的写入同时撤销正在进行的填充。通过 +8 KiB 等地址别名写入时，按实际 SRAM 低 13 位归一化；零字节使能不撤销缓存。非缓存读取的暂存结果继续保守失效，Boot 控制写入保留全局失效。AXI 已发事务保持稳定并排空。
- **提前接收 DMA 写响应。** 最后一拍 W 已接受且 R 已完成后即可握手 B，去掉进入 RESP 状态前的等待。独立定向测试中，即时 B 的最后 W 到 DONE 从 2 拍变为 1 拍；延迟 B 的测试仍为 8 拍。32 字分两次突发由 60→58 拍，跨 4 KiB 的 4+12 字突发由 40→38 拍，数据、错误和完成次数均正确。
- **缓存数据不复位。** 仅移除 1024 位数据阵列的复位，放到独立时钟过程；valid、填充长度、控制状态和 CPU 返回寄存器仍复位。成功填充一个字后才允许读取该字。此修改不减少执行拍数，目的在于降低数据阵列成本；冷启动未知值、复位和失效测试均通过。
- **FallThrough 只作功能试验。** 保留 `CUT_SLV_AX`、打开 `FallThrough` 时可进一步减少拍数，但本轮主候选仍为 0；没有为该选项完成新物理时序验证。

### 相同固件的 SoC 对比

所有候选复用本轮基线的原始固件，SHA-256 逐字节一致，保持原 testbench 和 10 ns 功能仿真时钟。下面的拍数从 commit 后到 CPU golden 自检结束，包含搬运、NPU 和检查，不是纯推理延迟，也不证明 100 MHz 物理频率。[完整对照和源文件记录](optimization_20261109/soc/comparison.json)。

| 标准 HAR 用例 | 已上传版 | 本轮候选 | 减少 |
| --- | ---: | ---: | ---: |
| seed 0，batch 4 | 3520 | 3471 | 1.39% |
| seed 1，batch 2 | 2494 | 2432 | 2.49% |
| seed 2，batch 1 | 1966 | 1919 | 2.39% |
| 训练 seed 10000，batch 4 | 3510 | 3462 | 1.37% |

| 配置 | 训练 HAR | 128 次 SRAM 写入 + HAR | 自修改代码 + HAR |
| --- | ---: | ---: | ---: |
| 已上传基线 | 3510 | 7748 | 3636 |
| 仅 DMA 响应优化 | 3477 | 7714 | 3602 |
| 仅按行失效 | 3495 | 4531 | 3584 |
| 按行失效 + DMA | 3462 | 4497 | 3550 |
| 上述 + 数据不复位 | 3462 | 4497 | 3550 |
| 上述 + FallThrough（未采用） | 3356 | 4261 | 3441 |

原 HAR 固件没有栈，循环主要从 SRAM 读取并向 NPU MMIO 写入，因此按行失效只节省少量尾部写入成本。`scratch_128` 在完整 HAR 前运行 128 次 SRAM 写循环，适合观察代码与数据共享 SRAM 时的影响。`code_patch_alias_byte` 则先执行指令返回 1，通过 SRAM 别名的单字节写改为返回 2，再通过正常地址的字写改为返回 3，每次执行 FENCE.I，随后完成原 HAR 自检。两项附加测试均通过，不能把它们的改善当作普通 HAR 收益。

独立 NPU+DMA 固定 seed 10000、相同确定性背压的 batch 1/2/4 为 **1401/1431/1541→1328/1377/1480 拍**，分别少 5.21%/3.77%/3.96%。这些数字来自独立总线模型，不能与完整 SoC 的 NPU 计数混用。[独立性能结果](optimization_20261109/npu_perf.json)。

### 验证与复现

已通过 41 组 NPU 数值回归、8 组 DMA 响应专项、71 项取指协议检查、13 项真实 SoC 写入边界检查，以及原始记录中七种配置的四组 HAR、两个附加程序和冷启动 Debug 对照。新增 `$isunknown` 检查覆盖冷启动和复位，防止未知握手/有效数据被测试忽略。真实 SoC 边界测试的写入经过 Debug SBA→AXI→SRAM，取指端由 testbench 驱动；实际 CPU 固件执行由另一组 SoC 测试覆盖。这些测试未包含物理 JTAG TAP 或板测。

```bash
python test/int8/run.py --count 32 --trained
python test/int8/run_ifetch.py
python test/int8/run_ifetch_snoop_soc.py --out test/int8/runs/snoop_new
python test/int8/run_soc_xcelium.py --out test/int8/runs/soc_new --debug-cold
# 复现额外写入程序；另一种 workload 为 code_patch_alias_byte
python test/int8/firmware_workloads.py --workload scratch_128 --out test/int8/runs/inputs/seed_10000
python test/int8/run_soc_xcelium.py --out test/int8/runs/scratch_new --seed 10000 --firmware-dir test/int8/runs/inputs
```

NPU/DMA 单元回归使用 Icarus；取指及完整 SoC 使用 Xcelium。所有输出目录使用新路径，原始日志、固件和源文件哈希保存在 [证据目录](optimization_20261109)。

### 综合结果及最终选择

同一 Genus 19.17、TT 库、20 ns SDC、理想时钟下，新两版综合输入仅 `my_ifetch.sv` 和标注数据是否复位的工程元数据不同，其他 RTL/约束/流程一致。两版均正常退出；未解析引用、未驱动、多驱动、latch 均为 0。

| 版本 | 全 SoC 单元面积（含 SRAM） | 取指模块面积 | 最差 setup 余量 |
| --- | ---: | ---: | ---: |
| 已上传 49911b2 | 2.152504 mm² | 0.091344 mm² | +0.3398 ns |
| 按行失效 + DMA，数据仍复位 | 2.154559 mm² | 0.094154 mm² | +0.5936 ns |
| 按行失效 + DMA，数据不复位（保留） | **2.148261 mm²** | **0.087437 mm²** | **+0.4936 ns** |

去掉数据复位相对同组合有复位版节省 0.006298 mm²（总面积约 0.292%，取指模块约 7.13%），代价是 setup 余量减少 0.100 ns，两者 TNS 和违规路径都为 0。因此保留无数据复位作为面积取舍，不能把它描述为面积、时序全面占优。最终组合相对已上传版的总单元面积减少约 0.197%，收益很小，不是芯片尺寸大幅缩减。

空间规划两版均通过：核心 1648×1648 µm，计划含外围裸片 1.948×1.948 mm、3.794704 mm²。单元面积与裸片面积是不同指标；本轮没有新的放置布线结果。最差路径仍从下降沿 SRAM 事务复位寄存器，经 AXI 返回逻辑，到 NPU 读返回寄存器；下一轮物理优化应关注这条半周期路径。现有约束的部分外部输入零 slew、输出零负载假设未改变，未执行多角、CTS/布线、SDF 或板级验证。

最终源码保留 `FallThrough=0`。功能试验中的 FT 版本还能让训练用例从 3462→3356 拍，但其组合路径变化未做本轮综合比较，暂不进入所选实现。后续应先对所选版本完成新 PNR/布线后时序与 SDF，再决定是否启用 FT；不建议仅为这些测试继续堆 MAC 或扩大权重 bank。

[证据总索引](optimization_20261109/summary.json)、[有复位综合](optimization_20261109/synthesis/selective_dma_reset/evidence/ppa_summary.json)、[所选无复位综合](optimization_20261109/synthesis/selective_dma_noreset/evidence/ppa_summary.json) 保留源文件和报告哈希。原始 area、qor、时序路径、结构检查及完成日志同时归档。

---

## 2026-11-09：rtl-dev 与 CPU 取指优化集成

本次以 `rtl-dev@1eb6462` 为基线，从 `perf/ifetch-line-buffer@5da2148` 移入 4×8-word（128 B 数据）取指缓存，保留重构版 `CUT_SLV_AX` 和 `FallThrough=0`。CPU 内核文件未修改。新增精确非缓存地址访问、写入时失效、异常 AXI 填充排空处理；缓存范围限制为实际 8 KiB SRAM 和不可变的 32 B Boot 跳板。

以下是 Xcelium 完整 SoC RTL 对照，四份固件、原始 `tb_soc.sv`、10 ns 功能仿真时钟和行为 SRAM 均相同。周期从镜像 commit 后到 CPU 自检通过，包含数据搬运、NPU 执行和 golden 比较；不能当作纯推理周期，也不证明 100 MHz 物理时序。完整对照及源文件/固件 SHA 在 [comparison.json](ifetch_20261109/comparison.json)，最终版本原始日志和结果在 [integrated_final/results.json](ifetch_20261109/integrated_final/results.json)。

| 用例 | 原 rtl-dev | 集成后 | 减少 | NPU 原版→集成后 |
| --- | ---: | ---: | ---: | ---: |
| 随机 seed 0，batch 4 | 6368 | 3520 | 44.72% | 982→986 |
| 随机 seed 1，batch 2 | 4257 | 2494 | 41.41% | 880→881 |
| 随机 seed 2，batch 1 | 3202 | 1966 | 38.60% | 832→835 |
| 训练模型 seed 10000，batch 4 | 6369 | 3510 | 44.89% | 975→976 |

训练用例的硬件周期计数为 6364→3505；testbench 观测边界比硬件多 5 拍。主要收益来自 CPU 取指，而非 MAC 发射数下降；FC1/FC2 每样本依然为 64/16 拍。NPU 多出的少量周期反映总线争用变化。冷启动 Debug 也通过，61 拍进入 halted、`boot_ready=0`、PC=`0x82c`。这里的装载注入在 Debug SBA 请求边界，未重新进行物理 JTAG TAP 或 FPGA 板测。

同时修复了单样本 Argmax 的独立错误：进入 FINISH 的同一边沿仍在提交最后一次 FC2 累加，旧实现会锁存更新前的第 0 类得分。定向输入使最终分数为 `[2,1,0,0,0,0]` 时，旧版错误返回类别 1。现在第一次比较直接读取已经提交的第 0 类累加值，保持五拍比较，不增加执行周期。32 组随机、6 组训练批次及 3 组上升/下降/并列定向用例共 41 组通过；见 [回归结果](ifetch_20261109/npu_result.json) 和 [旧版失败日志](ifetch_20261109/argmax_baseline_failure.log)。

后续优先考虑：

1. **按地址失效取指缓存。** 当前任何 SRAM 数据写入都会清空全部指令缓存，虽保证一致性，但普通数据写入也会驱逐代码。可按实际 SRAM 写地址匹配缓存行，并同步处理正在填充的行；需覆盖地址别名、字节写和调试重装。
2. **提高权重传输和跨样本复用效率。** 固定 seed 10000 的 NPU+DMA 独立背压测试中，batch 1/2/4 分别为 1401/1431/1541 拍，摊到每样本为 1401/715.5/385.25 拍，三者均搬运 2240 B 权重、发起 36 个 DMA 命令。监测到 WAIT_TILE 为 1282/1195/1071 拍；这些数属于独立 testbench，不与上述 SoC 的约 976 拍混用。见 [性能结果](ifetch_20261109/perf_result.json) 和 [状态计数](ifetch_20261109/perf_profile.json)。当前证据优先支持减少传输等待；该测试未观察到读 FIFO 满造成停顿，因此不能据此声称增加 FIFO 或 MAC 就能加速。
3. **有条件评估 AXI FallThrough。** 独立实验保留 `CUT_SLV_AX`，仅改 `FallThrough=1`，训练用例为 3405 拍，比集成版再少 105 拍。它改变组合路径，本次主实现仍取 0；采用前需重新检查物理时序。

**新综合结果。** 当前 HDL 和 filelist 的冻结副本已完成 Genus 19.17 工艺映射与优化：全 SoC 单元面积 2.152504 mm²（包含 0.401444 mm² 主 SRAM 宏），取指模块 0.091344 mm²、CPU 0.369224 mm²、NPU 子系统 0.898708 mm²、DMA 0.037995 mm²。20 ns、TT、理想时钟和现有 SDC 下，最差 setup 余量 +0.3398 ns，TNS 和违规路径均为 0；未解析引用、未驱动、多驱动、latch 均为 0。面积预算检查通过，计划裸片 1.948×1.948 mm、3.794704 mm²，但尚无本版放置/布线后的实际结果。详见 [综合摘要](ifetch_20261109/synthesis/summary.json)、[原始面积](ifetch_20261109/synthesis/syn/my_soc_top/reports/area/area.rpt)、[原始时序](ifetch_20261109/synthesis/syn/my_soc_top/reports/timing/func_tt_1p80v_25c_timing.rpt)。

综合最差路径现为下降沿 SRAM 事务复位寄存器，经 AXI 返回/仲裁逻辑，到 NPU 读返回寄存器的半周期路径；后续时序优化应检查这条路径的高扇出和组合深度。现有 SDC 对部分外部输入采用零 slew、对 td_o 采用零外部负载，因此这里不是板级 IO 签核。上述优化没有扩大 MAC 阵列；本次未重跑 PNR、SDF 后仿或 FPGA 板测，历史 bitstream、DEF/GDS 和 SDF 不属于当前源码。

---

本节比较八项独立优化：

1. 消除 tile 之间固定的 `DRAIN -> WAIT_TILE -> ISSUE` 气泡；
2. 将 FC2 每 bank 的 8 个逻辑 tile 打包为 48 B，并在 W1 尾部启动两个 W2 bank 的跨层预取。
3. 复用乘法器完成 FC2 的 `6 输出×8 输入行` 计算。
4. 将共享 bank 从 64 个乘法器减为 32 个，同时保持 64 B bank 大小。
5. 在 AXI slave 的 AW/AR 地址通道增加控制寄存器边界。
6. 将 FC1 后的动态 sample/output 选择和 32×16 重定标乘法拆成三级流水。
7. 将 FC2 从每拍 4 输入行降为 2 输入行，并用单个比较器逐拍完成 Argmax。
8. 将内部累加、Argmax 和重定标输入从 signed 32 位收窄为 signed 22 位。

基准固定使用 seed=10000 的训练模型和输入。NPU 周期从 `START` 统计到 `DONE`，包含权重 DMA、MAC、requant 和等待时间。AXI ready/valid 采用 testbench 中同一个确定性伪随机背压序列，因此各阶段周期可直接比较。每次只运行一个 batch，避免前一测试的 AXI 状态影响结果。

AXI 地址通道切分前的三级重定标流水固定基准：

| 指标 | batch=1 | batch=2 | batch=4 |
| --- | ---: | ---: | ---: |
| NPU 单批周期 | 1395 | 1415 | 1514 |
| 每样本摊销周期 | 1395.0 | 707.5 | 378.5 |
| FC1 / FC2 发射周期 | 64 / 8 | 128 / 16 | 256 / 32 |

该基线的完整 SoC 使用 `NO_LATENCY`，ModelSim 观测 5121 拍，硬件周期为 5116 拍，DMA 读/写与 MAC 重叠分别为 269/268 拍。相对无重定标流水的 batch=1/2/4 周期 1395/1413/1512，重定标流水使 batch=1 保持不变，batch=2 和 batch=4 各增加 2 拍，主要来自 FC1 末尾的两个排空周期。

| 历史 batch=8 阶段 | batch=1 | batch=2 | batch=8 | 完整 SoC batch=8 |
| --- | ---: | ---: | ---: | ---: |
| 优化前 `d2aef34` | 1669 | 1723 | 2025 | 8777 |
| 零气泡交接 `5a9a618` | 1668 | 1707 | 1969 | 8681 |
| FC2 打包和 W2 预取 | 1401 | 1431 | 1808 | 8589 |
| `CUT_SLV_AX` 控制切分（历史 batch=8） | 1401 | 1431 | 1808 | 10691 |

batch=4 为 FPGA 容量进一步做了两项局部修改：

```text
权重 bank 强制映射为寄存器，避免 1024 个 LUTRAM 占用 LUT 站点
4 个 Argmax 改为 1 个共享 Argmax，FINISH 依次处理样本
```

batch=4 的寄存器映射调整使 NPU 周期从 1560 增至 1567；共享 64 MAC 后为 1503 拍，最终减为共享 32 MAC 后为 1512 拍。恢复 `NO_LATENCY` 后完整 SoC 为 5109 拍。

## 第一阶段：零气泡 tile 交接

最后一个样本发射时立即产生 `consumed`，不再额外进入 `DRAIN`。若下一 bank 已发布，核心直接进入下一 tile；只有下一 bank 尚未准备好时才进入 `WAIT_TILE`。

| 指标 | 优化前 | 优化后 | 变化 |
| --- | ---: | ---: | ---: |
| batch=1 | 1669 | 1668 | -0.06% |
| batch=2 | 1723 | 1707 | -0.93% |
| batch=8 | 2025 | 1969 | -2.77% |
| 完整 SoC | 8777 | 8681 | -1.09% |

该阶段证明固定气泡被移除，但 batch=8 的实际收益小于理论上限，因为部分下一 tile 尚未完成 DMA，原有气泡被真实等待替代。

## 第二阶段：FC2 打包和 W2 早期预取

FC2 原始权重为 32 个逻辑 tile，每个 tile 只有 6 B。原实现按 tile 补齐到 8 B 并产生 32 次两字 DMA。新实现每 8 个逻辑 tile 连续打包为 48 B，共 4 次十二字 DMA：

```text
原格式：32 × 8 B  = 256 B
新格式： 4 × 48 B = 192 B
```

每个 64 B bank 保存一组 48 B 有效数据。该阶段只减少 DMA 事务和等待，当时核心仍按 32 个逻辑 tile 计算；后续共享 MAC 阶段把每个物理包扩展为 8×6 个乘积。W1 tile31 仍占用一个 bank 时，另一个已释放的 bank 立即预取第一个 W2 组；该 bank 在 requant 期间完成发布。tile31 释放后，第二个 bank 再预取第二组。FC2 开始后，每消费完一组即可继续预取下一组。

| 指标 | 第一阶段 | 第二阶段 | 变化 |
| --- | ---: | ---: | ---: |
| batch=1 | 1668 | 1401 | -16.01% |
| batch=2 | 1707 | 1431 | -16.17% |
| batch=8 | 1969 | 1808 | -8.18% |
| 完整 SoC | 8681 | 8589 | -1.06% |

相对最初基线，batch=8 从 2025 拍降到 1808 拍，单批延迟降低 10.72%，每样本从 253.1 拍降到 226.0 拍，等效吞吐率提高 12.0%。完整 SoC 自检从 8777 拍降到 8589 拍，降低 2.14%。

在这一历史阶段，`fc1_cycles` 和 `fc2_cycles` 仍分别为 `32×batch`；收益来自减少 DMA 事务、等待周期和 tile 交接气泡。下一阶段才改变 MAC 数量和 FC2 算术调度。

## 第三阶段：共享 64 乘法器

FC1 和 FC2 不会同时计算。原实现为 FC1 保留 64 个乘法器，又为 FC2 增加 6 个专用乘法器，共 70 个。新实现让同一个 64 乘法器 bank 按层重配置：

```text
FC1：32 output × 2 lane，使用全部 64 lane
FC2：6 output × 8 input row，使用前 48 lane
```

FC2 的一个 48 B 物理包不再拆成 8 个 6 B ISSUE tile，而是在一拍内完成全部 48 个有效乘积，并把每行乘积累加到对应 INT32 score。FC2 从 `32×batch` 个发射周期降为 `4×batch`。

| 指标 | 独立 MAC | 共享 MAC | 变化 |
| --- | ---: | ---: | ---: |
| 乘法器数量 | 70 | 64 | -8.57% |
| batch=1 NPU 周期 | 1401 | 1394 | -0.50% |
| batch=2 NPU 周期 | 1432 | 1410 | -1.54% |
| batch=4 NPU 周期 | 1567 | 1503 | -4.09% |
| FC2 发射周期 batch=4 | 128 | 16 | -87.50% |
| 完整 SoC batch=4 | 5193 | 5101 | -1.77% |

FC2 只剩 4 个物理包，两个 bank 仍需 ping-pong；当后续 W2 包尚未完成 DMA 时，缩短的计算段会把部分等待暴露出来，因此 NPU 总周期降幅小于 FC2 发射周期的降幅。

## 第四阶段：共享 bank 减半为 32 MAC

完整基准中 MAC 只在少量周期工作：batch=4 的 FC1 和 FC2 ISSUE 在 64-MAC 版本合计 144 拍，而 NPU 总周期为 1503 拍。长 DMA 等待为缩小计算阵列提供了空间。

最终 bank 仍为 64 B，改为两个计算相位：

```text
FC1：16 output × 2 lane，每样本每 tile 两拍
FC2：4 input row × 6 output，每 packet 两拍
```

同一权重 bank 在所有样本和两个相位完成后才释放，不增加 SRAM 权重流量。FC2 每相位只使用 24 个乘法器，其余 8 个空闲；FC1 使用全部 32 个。

| 指标 | 共享 64 MAC | 共享 32 MAC | 变化 |
| --- | ---: | ---: | ---: |
| 乘法器数量 | 64 | 32 | -50% |
| batch=1 NPU 周期 | 1394 | 1395 | +0.07% |
| batch=2 NPU 周期 | 1410 | 1413 | +0.21% |
| batch=4 NPU 周期 | 1503 | 1512 | +0.60% |
| FC1 ISSUE batch=4 | 128 | 256 | +128 |
| FC2 ISSUE batch=4 | 16 | 32 | +16 |
| 完整 SoC batch=4 | 5101 | 5109 | +0.16% |

新增的 144 个 MAC 时隙几乎全部落入原 DMA 和 bank 等待，因此 batch=4 总周期只增加 9 拍。该结果支持“以一半乘法器面积维持近似延迟”的硬件取舍。

## 第五阶段：控制切片评估与降频决策

`NO_LATENCY` 让 CPU、AXI crossbar、DMA 和 NPU 控制逻辑处于同一条组合路径，旧 50 MHz batch=2 FPGA 最差路径达到 42 级逻辑。曾评估 `CUT_SLV_AX`，历史 batch=8 配置中的代价为：

```text
NPU batch=1/2/8：1401 / 1431 / 1808，保持不变
完整 SoC batch=8：8589 -> 10691，增加 2102 拍
```

这会增加 MMIO 和 AXI 地址事务的固定延迟。`CUT_ALL_PORTS` 会把历史 batch=8 完整 SoC 增至 17938 拍。三级重定标流水后的新综合中，剩余最差路径转移到 CPU IF/ID → AXI Crossbar AR → AXI2NPU → NPU 地址/读数据选择，slack 仅 `+0.8 ps`，因此当前 ASIC RTL 改为 `CUT_SLV_AX`。功能与 ModelSim 回归通过；完整 SoC 总周期从 AXI 切分前的 5121 拍增至 6337 拍，增加 1216 拍。若继续使用 FPGA bitstream，也必须重新综合验证。

## 第六阶段：重定标三级流水

流水前 Placement 的第一条路径位于 FC1 重定标，而不是 MAC：

```text
quant_sample_reg[0]/Q
→ a1[quant_sample][tile_index_o] 动态选择
→ requant 32×16 乘法器
→ 舍入、移位和饱和
→ h_reg[3][20]/D
```

该路径 Required `19.467 ns`、Arrival `33.371 ns`、Slack `-13.904 ns`。其中动态 sample/output MUX 约占 20.1 ns，requant 乘法器组合阵列约占 10.2 ns。此前尝试在 MAC 后插入 512 bit 乘积流水，没有切中该路径，反而增加面积，因此已撤销。

当时 RTL 改为：

```text
第一级：选择 sample 和一个 8 输出组，寄存 8×32 bit
第二级：从 8 个输出中选 1，寄存 32 bit
第三级：32×16 乘法、舍入、移位、饱和并写 h
```

吞吐仍为每拍一个隐藏输出，FC1 末尾增加两个排空周期。

| 指标 | 无重定标流水基线 | 三级重定标流水（AXI 切分前） | 变化 |
| --- | ---: | ---: | ---: |
| batch=1 NPU 周期 | 1395 | 1395 | 0 |
| batch=2 NPU 周期 | 1413 | 1415 | +2 |
| batch=4 NPU 周期 | 1512 | 1514 | +2 |
| FC1 ISSUE 周期 batch=4 | 256 | 256 | 0 |
| FC2 ISSUE 周期 batch=4 | 32 | 32 | 0 |
| 完整 SoC testbench 周期 | 5109 | 5121 | +12 |
| 硬件 SoC 周期 | 5104 | 5116 | +12 |
| DMA 读/MAC 重叠 | 270 | 269 | -1 |
| DMA 写/MAC 重叠 | 269 | 268 | -1 |

本次完整回归为 38/38 单元用例、训练模型逐值对照、Boot 周期起点、冷启动 Debug 定向测试和完整 SoC ModelSim 自检全部通过。

## 第七阶段：FC2 串行归约与顺序 Argmax

上一轮 placement/preCTS 的第一条路径仍在 FC2：

```text
tile_index
→ FC2 输入/权重动态选择
→ INT8 乘法器
→ CSA 累加树
→ a2
```

为缩短这条路径，FC2 仍使用每个 48 B 物理包，但不再一拍处理 4 个输入行，而是拆成四个相位：

```text
FC2：6 output × 2 input rows，共四个相位
每相位有效乘积：12
每样本 FC2 ISSUE 周期：16
```

FINISH 同时删除单周期六路 Argmax，改为一个共享的 32 位有符号比较器和 best/class 寄存器。每个样本先装入类别 0，再逐拍比较类别 1..5；平局仍保留较小类别号。

| 指标 | 三级重定标流水 | 串行 FC2 + 顺序 Argmax | 变化 |
| --- | ---: | ---: | ---: |
| batch=1 NPU 周期 | 1395 | 1401 | +6 |
| batch=2 NPU 周期 | 1415 | 1431 | +16 |
| batch=4 NPU 周期 | 1514 | 1541 | +27 |
| batch=1 每样本周期 | 1395.0 | 1401.0 | +6.0 |
| batch=2 每样本周期 | 707.5 | 715.5 | +8.0 |
| batch=4 每样本周期 | 378.5 | 385.25 | +6.75 |
| FC2 ISSUE batch=1/2/4 | 8 / 16 / 32 | 16 / 32 / 64 | 翻倍 |
| 完整 SoC 总周期 | 6337 | 6369 | +32 |

最新完整 SoC 总周期为 6369 拍。固定基准下 DMA 与 MAC 的重叠为：

| batch | 读重叠 | 写重叠 |
| --- | ---: | ---: |
| 1 | 39 | 38 |
| 2 | 70 | 66 |
| 4 | 152 | 151 |

该版本每条 FC2 累加器路径每拍只归约两个乘积，Argmax 也从六路组合比较树变为五次顺序比较。代价是 batch=1/2/4 的 NPU 周期分别增加 6/16/27 拍，batch=4 每样本仅增加 6.75 拍。能否真正缩短 placement/preCTS 路径仍需新的综合和物理实现确认。

## 第八阶段：INT22 内部累加

最新 RTL 将 FC1/FC2 累加器、Argmax 比较器和重定标流水寄存器从 signed 32 位收窄为 signed 22 位。外部 bias 与 score MMIO 仍是 32 位字：bias 只解释低 22 位符号数，score 由 INT22 结果符号扩展。重定标乘法从 32×16 缩为 22×16，中间积从 48 位缩为 38 位。

22 位覆盖任意 INT8 输入和权重的通用 FC1 范围，并覆盖当前训练 bias 下的完整可达上界。随机回归已改为 INT22 补码回绕，边界 bias 使用 `-2^21` 和 `2^21-1`。周期、综合面积和时序收益尚待用户本地功能回归及新一轮 EDA 验证，不能在此阶段引用上一版结果。

同源 `9970d6f` 已完成综合与 Innovus 01–34。相对 32 位累加版本，Cell Area 和 NPU 面积均明显下降：

| 指标 | 32 位累加版 | INT22 | 变化 |
| --- | ---: | ---: | ---: |
| 全 SoC Cell Area | 2,207,733 µm² | 2,062,446 µm² | -145,287 µm²（-6.58%） |
| Cell 数量 | 71,041 | 65,636 | -5,405 |
| NPU 子系统面积 | 1,042,325 µm² | 896,961 µm² | -145,364 µm²（-13.95%） |
| NPU core 面积 | 708,953 µm² | 563,211 µm² | -145,742 µm²（-20.56%） |
| NPU flop 面积 | 543,040 µm² | 465,400 µm² | -77,640 µm²（-14.30%） |

最终 post-filler 逻辑密度为 73.094%，含 PAD Die 为 3.795639 mm²。20 ns 下 Setup/Hold WNS 为 **+0.032/+0.019 ns**，TNS 与违规路径均为 0；最终关键路径已转移到 CPU ALU，不再位于 NPU 加法树。完整记录见 [int22_validation.json](int22_validation.json)。

同源最终网表的 MAXIMUM SDF 后仿完成：11/11 用例功能通过，SDF annotation error、缺失实例和未匹配 timing check 均为 0；所有工作窗口和最终复位阶段动态时序事件为 0。每个 SDF 用例仍有 108 条初始复位事件，另有 10 条负 IOPATH 被仿真器截零，均作为已知限制保留。SRAM 输入/输出 Setup/Hold 四类各报告的 20 条路径全部 MET，最差 slack 分别为 6.222/10.061/2.685/11.524 ns。完整报告见 [INT22 EDA 结果](../eda/results/int22_20261104/README.md)。

## 验证

INT22 之前的 `2931fe0` RTL 曾在用户本地通过：

```bash
python test/int8/run.py --count 32 --trained --soc
```

共 38 个单元用例，覆盖 batch=1/2/4、24 条训练输入、量化边界值、DMA 错误、非法 bank 写、复位和服务完整 AXI SoC 自检。当前 16-MAC 版本的单元测试断言 FC1/FC2 发射周期分别符合 `batch×128` 和 `batch×16`，成功一批仍加载 64 个逻辑 tile；进入 FC2 前必须已经发起 W2 预取，且发布中的 bank 不得被 DMA 覆盖。下文其他 32-MAC 周期与 PPA 数字属于该次变更前的历史证据。

固定单批周期可复现为：

```bash
python test/int8/perf.py
```

该历史记录见 [shared_mac_validation.json](shared_mac_validation.json)。它只对应 32 位累加版本，不能作为当前 INT22 RTL 的功能或周期证据。

上述历史周期数字仍是 RTL 功能仿真，不是物理签核。INT22 的 34 步物理结果和 SDF 后仿已经具备；独立 foundry DRC/LVS、正式 LEC 和 IR/EM/ESD 仍不属于该流程的通过范围。
