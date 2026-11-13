# Wire Bond实测修复与复位问题跟进

be4a7fc候选完整综合/34步/环境EDA整理均0；901个物理文件核验。含PAD Die3.7956390976mm²，原生Density74.992%，TT Setup/Hold+3.765/+0.091ns。
最终同GDS的64项Wire Bond检查从9条降为0；Lab5原生LVS CORRECT、天线0、课程DRC通过，ERC原始残项逐对象列明，不称ERC Clean。
61项Lab5文件已SHA回传。正式修复为34个固定PAD上的M5/M6原生信号布线避让，2.5µm规则未修改。

**该候选整体尚未验收：TT 17例功能通过、绑定完整且负IOPATH截零0，但最终复位有两条真实动态违规。**
这两条不能由静态通过或功能PASS豁免。[候选实际数据](candidate_be4.json)保存同源结果和回传身份。

原始SDF、模型、固件、激励保持SHA不变的被动波形复现确认：上游复位先改变AXI地址/ready，SRAM桥仍在额外的延迟复位窗口。
新全局复位方案及功能证据见[系统复位修复](../../../report/system_reset_boundary.md)。新RTL必须重新综合、实现、TT SDF和Lab5，不能复用本候选验证新RTL。

本地证据：`lab5/wire_bond_fix_be4a7fc_20261113/{implementation,postsim_tt,lab5}`；大文件留服务器。
本轮只更新xzx，不合入main；main已有独立NPU更新，不能由本次历史RTL输入证明。未做Dummy后提取STA、IR/EM或完整代工厂签核。
