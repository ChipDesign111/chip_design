# Changelog

## Full SoC physical implementation — 2026-10-21

- 完成完整 SoC 的 Innovus floorplan、IO、电源、布局、CTS、布线与导出；课程 TT 下最终 setup +1.217 ns、hold +0.018 ns，独立物理审计 8/8 通过。
- 在明确的 1000 ns 先复位后起钟协议下完成 MAX/MIN 与自测/DMA 四个完整 SDF 场景，保留早期失败记录、原始 STA 和仿真兼容处理边界。
- 保存公开验收摘要、两张实际 DEF/LEF 版图预览和 14 页课程汇报 PPT。完整数据库、工艺原始视图和大日志保留在私有工作目录。
- 将无需 EDA/PDK 的审计器回归加入 CI，并让并发清理测试通过双 worker 屏障确定进入被测分支，避免依赖 Windows 进程启动速度。

## ASIC flow and boot wait — 2026-10-20 to 21

- 新增完整 SoC 的 TSMC180 Genus 工艺综合、Xcelium 前仿、门级功能及 SDF 后仿流程，固定输入哈希并严格核对原始日志。
- 修复上电直接执行空 SRAM 的启动问题：boot RAM 首条指令改为等待循环，经 JTAG 下载、回读、发布启动字后再复位运行；原 SHA 与集成修改记录保留。
- 保留原四级同步器，在 SoC 顶层增加下降沿复位释放寄存器，处理真实 SDF 暴露的 recovery/removal 余量问题。
- 适配既有 SoC 预加载测试台，保持 NPU 算术、39/59 周期、CPU/DMA 真实模型和 AXI 传输判据。实测状态与后续物理实现范围见 [EDA 结果](../eda/RESULTS.md)。

## Unreleased — 2026-10-15

- 顶层业务目录统一为 rtl / fpga / model / eda / test / report / tools。
- 完整 SoC 收入 rtl；仅保留当前 HAR NPU，删除原 NPU、4×4 测试及旧导入入口。
- 默认主存统一为 portable-sram，授权环境可选 ra1shd；旧 reference 配置移除。
- 测试按日期归档，每次运行独立保留脚本快照、源 SHA、结果和报告；工具入口改为 python tools/project.py。
- 厂商资料移至 tools/local；fpga 与 eda 保持空占位。

## Prior baselines

2026-10-13：tiled MLP、真实模型及工程化验证。2026-10-15：主 SRAM 宏功能接入。具体实测记录按日期见 [test](../test/README.md)。

## DMA integration

新增独立 AXI burst DMA，用于主 SRAM 到 NPU 参数/输入装载；最多 16-word 缓冲，新增 0xD00 CSR。显式更新两个 SoC 集成文件及其来源记录，保持算术核心和原寄存器兼容。增加协议、并发、错误、复位与真实模型端到端周期对比。见 [DMA](dma.md)。
