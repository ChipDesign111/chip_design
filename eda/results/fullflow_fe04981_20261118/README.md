# INT22 RAW GEMV 全流程 EDA 结果

本次结果绑定物理部署提交 `fe04981`，功能 RTL 为 `0e2d0cf`。物理、TT SDF 后仿和 Lab5 均由本机同一套 TSMC180 工具环境执行。

## 物理实现

- Genus 综合与 Innovus 01–34 完整通过，四个阶段入口退出码均为 0。
- 含 PAD Die：`3.7956390976 mm²`，低于 `3.8 mm²`。
- 最终原生 Density：`75.005%`。这是用户明确接受的非默认例外；本次没有继续执行 1649 µm 核心重跑。
- TT Setup WNS：`+0.194 ns`，目标 `+0.10 ns`。
- TT Hold WNS：`+0.050 ns`，目标 `+0.05 ns`。
- Setup/Hold TNS 均为 0，违规路径均为 0。
- Setup 电气 DRV 的 max-cap、max-transition、max-fanout、max-length 均为 0。
- 第 33 步 default DRC、天线、Placement、完整核心 PG 和常规信号连通通过。

## TT SDF 后仿

后仿绑定同一 `fe04981` 最终数据库，共 18 组：17 组 SDF 和 1 组独立 unit-delay 对照。

- 功能通过 18/18，`normal_postsim_pass=true`。
- SDF 回标 error 0、缺失实例 0、缺失时序检查 0。
- 全部阶段动态时序违规 0，负 IOPATH 截零 0，负路径支持完整。
- 新增 RAW SoC 场景 `sdf_raw_tail_33x65` 通过：CPU 观测 188032 周期、4 个 RAW tile、33×65 非整齐输入输出、66 次 RAW 部分和读回，没有动态时序违规。
- legacy 16 个 SDF 复位相位及 unit-delay 对照全部通过。

## SRAM 半周期 STA

| 路径组 | 最差 Setup | 最差 Hold |
| --- | ---: | ---: |
| SRAM 输入 | `+6.187 ns` | `+10.157 ns` |
| SRAM 输出 | `+3.047 ns` | `+11.501 ns` |
| Reset→request | `+5.729 ns` | `+11.493 ns` |

所有报告路径 slack 均非负。

## Lab5

Lab5 完成输入审计、CDL 转换、Seal Ring/POC、pre/post dummy DRC、金属及 OD/PO dummy、LVS、ERC、天线和 Wire Bond。

- `lab5_pass=true`。
- LVS CORRECT，605 条 trace property 核对。
- 天线 62 项、Wire Bond 64 项，违规均为 0。
- post-dummy DRC 的剩余非课程排除项为空。
- ERC 并非 Clean：保留经逐对象识别的原生 PAD 和隔离外衬底课程残项，不作整体豁免。
- 原物理输入在 Lab5 前后 SHA 一致。

大型数据库、SDF、SPEF、GDS、DEF 和授权模型保留在本地上传目录 `eda_runs/uploads/20261118_fe04981_1`。本报告不宣称独立 foundry DRC/LVS、多 PVT、SI、IR/EM/ESD、板级或形式等价签核。
