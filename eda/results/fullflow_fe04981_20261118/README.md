# INT22 RAW GEMV 全流程 EDA 结果

本次结果绑定物理部署提交 `fe04981`，功能 RTL 为 `0e2d0cf`。物理、TT SDF 后仿和版图完成与签核均由本机同一套 TSMC180 工具环境执行。

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

后仿绑定同一 `fe04981` 最终数据库，共 24 组：23 组 SDF 和 1 组独立 unit-delay 对照。当前新增测试没有修改 RTL，因此复用同一版后网表和 TT SDF。

- 功能通过 24/24，`normal_postsim_pass=true`。
- SDF 回标 error 0、缺失实例 0、缺失时序检查 0。
- 全部阶段动态时序违规 0，负 IOPATH 截零 0，负路径支持完整。
- 动态 RAW `sdf_raw_tail_33x65` 通过：CPU 观测 188032 周期、4 个 RAW tile、33×65 非整齐输入输出、66 次 RAW 部分和读回，没有动态时序违规。
- 预打包 RAW 三组通过：`32×64` 满块、`33×65` 尾块和 CPU→RAW→CPU 三层，分别观测 4441、7503、12216 个 SoC 周期；均直接读取镜像中预排的 W1 权重，运行时权重重排为 0。
- 无完整 RAW 块的 CPU-only 三层回退通过，观测 5591 周期。
- HAR 加速比使用的 CPU/HAR batch=4 成对固件均通过门级功能；分别观测 154661/3371 周期。这里的后仿周期包含自检，不替代前仿 BEGIN/END 加速比。
- Legacy HAR 16 组 SDF、15 相位复位扫描及 unit-delay 对照全部通过。

RAW 和 CPU-only 后仿记录的是从 CPU 提交镜像后到自检 magic 的完整 SoC 周期，包含 golden 检查和固件清理，不是纯推理 BEGIN/END 区间，不能与前仿加速比周期直接相减。

## SRAM 半周期 STA

| 路径组 | 最差 Setup | 最差 Hold |
| --- | ---: | ---: |
| SRAM 输入 | `+6.187 ns` | `+10.157 ns` |
| SRAM 输出 | `+3.047 ns` | `+11.501 ns` |
| Reset→request | `+5.729 ns` | `+11.493 ns` |

所有报告路径 slack 均非负。

## 版图完成与签核

版图完成与签核流程完成输入审计、CDL 转换、Seal Ring/POC、pre/post dummy DRC、金属及 OD/PO dummy、LVS、ERC、天线和 Wire Bond。历史 `Lab5` 路径通过兼容符号链接保留。

- `layout_signoff_pass=true`。
- LVS CORRECT，605 条 trace property 核对。
- 天线 62 项、Wire Bond 64 项，违规均为 0。
- post-dummy DRC 的剩余非课程排除项为空。
- ERC 并非 Clean：保留经逐对象识别的原生 PAD 和隔离外衬底课程残项，不作整体豁免。
- 原物理输入在 Lab5 前后 SHA 一致。

大型数据库、SDF、SPEF、GDS、DEF 和授权模型保留在本地上传目录 `eda_runs/uploads/20261118_fe04981_1`。本报告不宣称独立 foundry DRC/LVS、多 PVT、SI、IR/EM/ESD、板级或形式等价签核。
