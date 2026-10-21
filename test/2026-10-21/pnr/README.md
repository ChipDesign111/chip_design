# 完整 SoC 布局布线与布线后验证

本轮固定使用启动/复位修复后的完整 CV32E40P + AXI + DMA + NPU 综合网表，输入身份和实际结果见 [物理实现记录](../../../eda/pnr/RESULTS.md) 与 [机器摘要](summary.json)。本目录与布线前综合结果分开保存。

[版图预览与来源](figures/README.md) 保存两张实际 DEF/LEF 几何渲染；[汇报 PPT](../../../report/slides/HAR_SoC_ASIC_implementation_20261021.pptx) 汇总本轮工作。

当前 Innovus 布局、CTS、详细布线和导出已完成，独立物理审计与静态约束覆盖分类已通过。原 late 3,138、early 3,220 个未测试项保留；额外 82 条 hold 均逐项匹配既有 CDC 例外，没有新增时序例外。

布线后动态结果为 **PASS**，限于下述明确的外部上电协议。原 MAX 基线在上电最初约 12 ns 有 3 条 setup 违规，即使软件两次运行完成也严格判 FAIL；旧 MIN 两个完整场景的 PASS 单独保留。现用[并行入口](../../../eda/pnr/run_postroute_parallel.py) 的 `--poweron-settle-ns 1000`，在复位有效时先保持系统时钟低 1000 ns，再运行原 20 ns 时钟；首次上升沿为 1010 ns，复位释放为 1160 ns。仅派生测试台的时钟发生器一个区域发生变化，原测试台、RTL、固件和全部时序检查不变。

该协议下的 MAX/MIN 5000 ns 启动 smoke 无违规，但不作为完整验收。新的 MAX/MIN × 自测/DMA 四个完整场景均已实际 PASS，每场景两次启动、2048 字下载回读、0 条时序诊断；实际耗时、注入统计、原始完成标记和审计哈希见[机器摘要](summary.json)。上电自由运行时钟若属于产品要求，仍需设计保障和另行验证；协议边界见 [启动说明](../../../eda/BOOT_PROTOCOL.md)。

原始报告、数据库、DEF/GDS/SPEF/SDF、仿真日志及真实几何预览保存在私有工作目录和后续交付包，工艺原始视图不进入 Git。范围是课程名义 TT 流程；独立 foundry DRC/LVS、全 PVT、IR/EM 与开发板验证需另行完成。
