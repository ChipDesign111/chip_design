# 16-MAC SoC MAXIMUM SDF 后仿

本目录对应最终物理结果 [int8_16mac_20261113](../README.md)，使用同一 EDA 数据库导出的层次网表、原 SDF 和完整 SoC firmware。后仿修复提交为 `c2a7339`，物理部署提交为 `c02527e`。

## 结果

| 检查 | 结果 |
| --- | --- |
| 功能通过 | **11/11** |
| MAXIMUM SDF 用例 | 10 |
| unit-delay 无 SDF 对照 | 1 |
| SDF 回标 error | **0** |
| 缺失实例 | **0** |
| 未匹配 timing check | **0** |
| 工作窗口动态时序违规 | **0** |
| 负 IOPATH 被 VCS 截零 | 21 |
| 每个 SDF 用例初始复位事件 | 28 |
| 最终复位事件 | 0 |

## 功能与周期

基础训练用例 `sdf_max`：

```text
observed CPU cycles = 2701
NPU cycles          = 952
DMA/MAC overlap     = 500
read overlap        = 466
write overlap       = 499
```

`gate_unit`：

```text
observed CPU cycles = 2700
NPU cycles          = 952
DMA/MAC overlap     = 500
read overlap        = 466
write overlap       = 499
```

SDF 与 unit-delay 的 NPU 周期和 DMA 重叠完全一致；CPU 观测相差 1 拍，来自 PAD、时钟和响应路径回标延时，不是 NPU 计算能力变化。

本矩阵还覆盖训练输入 `10001–10005` 以及随机固件 `1/3/5/7`，复位拉低相位从 250 ps 扫到 11450 ps；全部功能通过，所有动态时序事件都只位于初始复位阶段。

## unit-delay 对照

纯零延时、无 SDF 的第一次对照在取指行缓存/PAD 边界出现确定性组合竞态，CPU 自检得到 `0xdeadbeef`。保留 SDF 但关闭 timing check 仍复现；加入 `+delay_mode_unit` 后功能通过。因此当前对照使用 unit-delay，而不是把仿真器零延时竞态误判为 RTL/门级功能错误。

## 文件

- [audit.json](audit.json)：逐用例时序阶段和工作窗口洁净状态。
- [results.json](results.json)：11 个用例的功能与周期。
- [input_manifest.json](input_manifest.json)：网表、SDF、firmware、库模型和仿真适配器 SHA。
- [sdf.log](sdf.log)：SDF 回标原文。
- [sdf_max.log](sdf_max.log)、[gate_unit.log](gate_unit.log)：基础 SDF 和 unit-delay 完整日志。
- [review.tar.gz](review.tar.gz)：47 个轻量审核文件。

## 范围

`active_window_dynamic_timing_clean=true` 只表示固件装载、CPU 启动和自检工作窗口内没有动态 timing violation。每个 SDF 用例仍有 28 条初始复位 timing event，另有 21 条负 IOPATH 被 VCS 截零；这些限制不能隐藏。独立 foundry DRC/LVS、多 PVT、IR/EM/ESD 和形式等价仍未执行。
