# 1948.8 µm Die 全流程与签核结果

本结果绑定物理部署 `1efd161`，功能 RTL 基线为 `19a0ce2`。当前 `main` 在物理部署之后只修改了 EDA 配置、floorplan 控制和后仿审核逻辑；`1efd161..HEAD` 的 `rtl/` 差异为空。用户接受的物理边界是 Die 不超过 1950 µm、Seal Ring 外框不超过 1980 µm。

## 物理实现

- Genus 与 Innovus 34 步完成；环境、EDA、结果收集和入口脚本退出码均为 0。
- 最终 DEF `DIEAREA` 为 `(0 0) (3897600 3897600)`，按 2000 DBU/µm 换算为 `1948.8 × 1948.8 µm`。
- 含 PAD Die 面积：`3.79782144 mm²`，低于 `3.8 mm²`。
- 原生 Density：`74.966%`。
- TT Setup/Hold WNS：`+0.481 / +0.050 ns`；TNS 均为 0，违规路径均为 0。
- max-cap、max-transition、max-fanout、max-length 违规均为 0。
- default DRC、PG、信号连通、天线和 Placement 检查通过。
- 映射叶实例 65,367；Cell Area `2,076,163.866 µm²`；SRAM Area `401,443.591 µm²`。

## TT SDF 后仿

后仿绑定同一物理上传的最终网表和 SDF，共 27/27 功能通过：26 组 SDF 加 1 组 unit-delay 对照。

- `normal_postsim_pass=true`，`benchmark_protocol_complete=true`，`benchmark_pair_errors=[]`。
- SDF 回标 error、缺失实例、缺失时序检查均为 0；负 IOPATH 截零为 0。
- 工作窗口动态时序事件 0，最终复位动态时序事件 0。
- 初始复位阶段保留 26 条事件，每个 SDF case 一条，均为 DMA 门控单元 `RC_CG_HIER_INST280` 的同一 `$setuphold` 检查。事件未被隐藏；`all_phase_dynamic_timing_clean=false` 如实记录。
- 10 组 benchmark 的 BEGIN→END 周期与前仿逐项一致。

| 场景 | CPU cycles | 后端 cycles | CPU/后端 |
| --- | ---: | ---: | ---: |
| RAW full 32×64 | 45624 | 4997 | 9.130278× |
| RAW tail 33×65 | 47397 | 9199 | 5.152408× |
| RAW CPU→RAW→CPU 三层 | 52606 | 13278 | 3.961892× |
| 动态 RAW tail 33×65 | 47397 | 189720 | 0.249826× |
| HAR batch4 | 153536 | 2612 | 58.781011× |

完整自检窗口仍单独保留，例如动态 RAW 为 190,969 周期，不能替代 BEGIN→END 加速比口径。

## SRAM 半周期 STA

| 路径组 | 最差 Setup | 最差 Hold |
| --- | ---: | ---: |
| SRAM 输入 | `+6.370 ns` | `+10.087 ns` |
| SRAM 输出 | `+2.815 ns` | `+11.619 ns` |
| Reset→request | `+5.651 ns` | `+11.748 ns` |

所有报告路径 slack 均为正。

## 版图完成与签核

- `layout_signoff_pass=true`，流程退出码 0。
- Die：`1948.8 × 1948.8 µm`，满足 ≤1950 µm。
- Seal Ring 外框：`1979 × 1979 µm`，满足 ≤1980 µm。
- LVS CORRECT，605 条 trace property 核对。
- post-dummy DRC 无未排除规则；Antenna 62 项 0 违规；Wire Bond 64 项 0 违规。
- ERC 并非 Clean：原生报告 12 项检查、7 个层次结果、977 个展开结果；课程流程逐对象接受 native PAD 和隔离外围衬底残项，不作整体豁免。
- 原 DEF、GDS、网表在签核前后 SHA 不变。

本结果不宣称独立 foundry DRC/LVS、多 PVT、SI、IR/EM/ESD、板级或形式等价签核。

## 证据位置

- 物理：`/home/s2400011035/chip-fullstack-2026/eda_runs/uploads/20261119_163338_1efd161`
- TT SDF：`/home/s2400011035/chip-fullstack-2026/eda_runs/uploads/20261119_163338_1efd161/postsim_tt_1`
- 版图完成与签核：`/home/s2400011035/chip-fullstack-2026/eda_runs/uploads/20261119_095620_layout_signoff_24f4886`
- 结果摘要：[summary.json](summary.json)

大型 GDS、DEF、SDF、SPEF、OA/Encounter 数据库和授权模型保留在服务器上传目录。
