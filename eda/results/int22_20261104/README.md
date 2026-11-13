# INT22 累加版：物理结果与 SDF 后仿

源码 `9970d6f` 的同源 INT8 64→32→6 SoC 已完成 Genus 综合、Innovus 01–34、结果收集和最终网表 SDF 后仿。含 PAD Die 为 **3.7956390976 mm² ≤ 3.8 mm²**，20 ns 下最终 Setup/Hold **+0.032/+0.019 ns**，TNS 和违规路径均为 0。最终关键路径为 CPU ALU，NPU 加法树已退出全局最差路径。

10 组 MAXIMUM SDF 和 1 组无 SDF 门级对照均通过功能自检。SDF 回标 error、缺失实例和未匹配 timing check 均为 0；工作窗口和最终复位阶段动态时序事件为 0。每个 SDF 用例仍有 108 条初始复位事件，另有 10 条负 IOPATH 被仿真器截零，均作为已知限制保留。

## 从哪些文件开始

| 文件 | 作用 |
| --- | --- |
| [summary.json](summary.json) | 物理、面积、时序、后仿来源和门禁结果 |
| [逐步运行报告](逐步运行报告.md) | Genus 到 Innovus 34 步的动作、参数和实际结果 |
| [step33](raw/step_33.json)、[step34](raw/step_34.json) | 最终时序、物理检查及导出检查 |
| [综合面积](raw/area.rpt)、[外框](raw/geometry.json) | 区分综合 Cell Area 与含 PAD Die |
| [最终布局](final_layout.gif) | 本版最终布局布线截图 |
| [SDF后仿](postsim/README.md) | 回标、11 组功能结果、复位事件和半周期 STA |

`raw` 保留最终 PG、DRC、天线、信号、placement、Setup/Hold 原始摘要和导出证据。大网表、SDF、SPEF、GDS、许可模型和编译数据库仅保留服务器。

## 面积和时序

| 指标 | 32 位累加版 | INT22 | 变化 |
| --- | ---: | ---: | ---: |
| 全 SoC Cell Area | 2,207,733 µm² | 2,062,446 µm² | -145,287 µm²（-6.58%） |
| Cell 数量 | 71,041 | 65,636 | -5,405 |
| NPU 子系统面积 | 1,042,325 µm² | 896,961 µm² | -145,364 µm²（-13.95%） |
| NPU core 面积 | 708,953 µm² | 563,211 µm² | -145,742 µm²（-20.56%） |
| Setup WNS | INT32 版本见历史结果 | +0.032 ns | 通过 |
| Hold WNS | +0.019 ns | +0.019 ns | 通过 |

最终 post-filler 有效逻辑密度为 73.094%，含 Filler 后为 100%。规划利用率和含 Filler 密度都不能替代有效逻辑密度。

## 最终检查

- 未摆放实例：0；
- Setup/Hold TNS：0/0；
- Setup/Hold 违规路径：0/0；
- max cap、transition、fanout、length 的 real/total 违规：0；
- 完整核心 VDD/VSS PG：`Found no problems or warnings`；
- 默认 DRC：0；
- 普通信号未解决连接：0，`VDDPST/VSSPST` 两项 IO 抽象限制按同源 GDS/placement 证据分类；
- 天线违规 net：0；
- DEF 顶层物理端口：10；
- GDS 未定义引用：0。

## SDF 后仿

| 项目 | 结果 |
| --- | ---: |
| MAXIMUM SDF 用例 | 10 |
| 无 SDF 对照 | 1 |
| 功能通过 | 11/11 |
| Annotation errors | 0 |
| 缺失实例 | 0 |
| 未匹配 timing check | 0 |
| Active 时序事件 | 0 |
| Final-reset 时序事件 | 0 |
| Negative IOPATH 截零 | 10 |

SRAM 输入/输出 Setup/Hold 四类半周期 STA 均全部 MET，最差 Slack 为 `+6.222/+10.061/+2.685/+11.524 ns`。详见 [后仿结果](postsim/README.md)。

## 保存位置与范围

物理工作区：

```text
/home/s2400011035/chip-fullstack-2026/eda_runs/uploads/20261103_int22_9970d6f
```

后仿工作区：

```text
/home/s2400011035/chip-fullstack-2026/eda_runs/uploads/20261104_191006_postsim_5edf6cd
```

物理输入 manifest：

```text
c8a503ab45c443bc28539376cda568e4d61273d34969b6f3956a7cf6883cce38
```

后仿回传包 SHA-256：

```text
54117accf66d58f285c5cecdc864a00d89a15edc4e297c42957e0ffccba14973
```

本结果适用于单 TT、1.8 V、25 °C、20 ns、MAXIMUM SDF 和所列有限输入/复位相位。尚未执行正式 LEC、独立 foundry DRC/LVS、多 PVT、IR/EM/ESD 或活动功耗重估。
