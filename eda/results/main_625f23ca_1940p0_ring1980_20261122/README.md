# 1940 µm Die、1980 µm Seal Ring 全流程结果

本轮源码提交为 `625f23ca`。物理实现、TT SDF 后仿、SRAM 半周期 STA 和版图完成与签核均从同一份冻结输入开始。

## 几何约束

- Die：`1940 × 1940 µm`，面积 `3.7636 mm²`。
- Seal Ring 参考内框：`(-5,-5)` 到 `(1945,1945) µm`，距 Die 每边 `5 µm`。
- 原生 Seal Ring 从参考内框向外占 `15 µm`。
- Seal Ring 外框：`1980 × 1980 µm`。
- Density 只报告，不作为本轮最终门禁。

## 物理实现

- Genus、Innovus 01–34、结果整理和入口脚本退出码均为 0。
- Density：`75.892%`。
- TT Setup/Hold WNS：`+0.230 / +0.050 ns`；TNS 均为 0，违规路径均为 0。
- max-cap、max-transition、max-fanout、max-length 违规均为 0。
- default DRC、Placement、完整核心 PG、信号连通和天线检查通过。

## TT SDF 后仿

- 27/27 功能通过：26 组 SDF 加 1 组 unit-delay 对照。
- `normal_postsim_pass=true`，`benchmark_protocol_complete=true`，`benchmark_pair_errors=[]`。
- SDF 回标 error、缺失实例、缺失检查、负 IOPATH 截零均为 0。
- 工作窗口 0 条、最终复位 0 条动态时序事件。
- 初始复位保留 26 条事件，每个 SDF case 一条；`all_phase_dynamic_timing_clean=false` 如实记录。
- 10 组 BEGIN→END benchmark 周期与前仿一致。

## SRAM 半周期 STA

| 路径组 | 最差 Setup | 最差 Hold |
| --- | ---: | ---: |
| SRAM 输入 | `+6.452 ns` | `+9.987 ns` |
| SRAM 输出 | `+2.635 ns` | `+11.643 ns` |
| Reset→request | `+5.367 ns` | `+11.570 ns` |

## 版图完成与签核

- `layout_signoff_pass=true`，流程退出码 0。
- LVS CORRECT。
- post-dummy DRC 无未排除规则；Antenna 62 项 0 违规；Wire Bond 64 项 0 违规。
- ERC Clean=false：保留逐对象识别的课程 native PAD/外围衬底残项，不作整体豁免。
- 原物理输入在签核前后 SHA 不变。

本结果不宣称独立 foundry DRC/LVS、多 PVT、SI、IR/EM/ESD、板级或形式等价签核。

## 证据

- 物理：`/home/s2400011035/chip-fullstack-2026/eda_runs/uploads/20261122_104205_625f23ca_die1940_ring1980_run3`
- TT SDF：`/home/s2400011035/chip-fullstack-2026/eda_runs/uploads/20261122_104205_625f23ca_die1940_ring1980_run3/postsim_tt_1`
- 版图完成与签核：`/home/s2400011035/chip-fullstack-2026/eda_runs/uploads/20261122_113608_layout_signoff_625f23ca_die1940_ring1980`
- 结构摘要：[summary.json](summary.json)
