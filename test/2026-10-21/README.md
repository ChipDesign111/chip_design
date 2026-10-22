# 2026-10-21 完整 SoC ASIC 验证

以 GitHub `52be8c57b365b70536500526a52905352e505666` 和两处有记录的启动/复位集成修改为输入，完成 TSMC180 TT 的 RTL 前仿、Genus 完整综合、门级功能后仿、综合后 MAXIMUM SDF 后仿及独立证据审计。随后完成完整 SoC 的 Innovus 布局布线与静态物理检查；布线后 SDF 在明确的 1000 ns 上电协议下，MAX/MIN 四个完整场景均已实际 PASS。

[综合前后仿验收摘要](asic/summary.json) 保存 92 个源文件哈希、工具版本、面积/setup、每组下载/双启动、综合后 SDF 注入及审计身份。该摘要保持原有布线前证据范围。[详细结果](../../eda/RESULTS.md)、[启动与复位协议](../../eda/BOOT_PROTOCOL.md)、[物理规划](../../eda/PHYSICAL_PLAN.md) 说明修改与边界。

完整网表、SDF、数据库和日志归忽略目录 `eda/work/asic-resetfall`、`eda/work/pnr-20261021-3400` 及私有证据包，工艺库原始模型不入仓库。

完整 SoC 最终 route / finish / export 为 0 tool errors，Die 3400.32 μm 见方，setup WNS +1.217 ns、hold WNS +0.018 ns，TNS、违反端点、DRV、最终布线 DRC 和天线违规均为 0，独立物理审计 8/8 PASS。原生 IO 的 no-routing 提示及预期 Bond 覆盖使用实际几何证据独立验收，详见 [PNR 结果](../../eda/pnr/RESULTS.md)。正式布线后 SDF MAX/MIN 四个场景已在明确的 1000 ns 上电协议下全部通过，每场景两次启动、2048 字下载回读、0 条时序诊断；不将布线前 PASS 或静态时序 PASS 当作动态后仿通过，也不声明全 PVT 或 foundry 签核完成。
