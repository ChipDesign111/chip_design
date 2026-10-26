# 扇出脚本修复版：密度上限阻止Hold修复

物理源码`bcc483e94bdf8ae8836ffcbb05eebf673b9ffa2b`，独立上传目录`/home/s2400011041/Desktop/fullstack_chipdesign/uploads/20261027_040030_bcc483e`。环境退出0，EDA在32步审计处退出1，最后通过的步骤为31；没有完成34步或生成可用于本轮验收的新SDF。

首批676个扇出ECO目标全部执行成功，总计847次分流后，最终诊断摘要中扇出和电容违规为0。完整5轮Setup/Hold修复之后，聚合Setup +0.014ns、TNS 0、违规路径0；Hold −0.829ns、TNS −13.686ns、违规路径138，未达到最低+0.10ns。实际转换时间违规网络681个。整颗几何面积3.7956390976mm²，工具报告逻辑密度81.445%。这些是失败时诊断，不能视为最终验收。

关键证据是[工具摘录](density_and_failure_excerpt.log)：初始化的`setOptMode -maxDensity`为75%，每轮Hold优化到核心修复阶段，均显示因超过75%密度而停止。规划参数target_utilization=85%只参与规划检查，没有修改该初始化选项。因此继续重复相同5轮不能消除这个阻塞。

修复新增显式optimizer_max_density=0.85，环境准备将它写入user_define.tcl，再用于物理初始化。它允许优化器在85%以内增加修复单元，不改变固定核心、20ns、整颗≤3.8mm²或时序/物理验收。配置拒绝非有限值、低于规划利用率或高于85%的值。实际Python配置读取、Tcl选项传递及75项保留硬件SHA检查通过；实际物理效果必须由新上传的完整流程验证。

保留[Setup摘要](my_soc_top_postRoute.summary.gz)、[Hold摘要](my_soc_top_postRoute_hold.summary.gz)、[状态](summary.json)、[诊断](diagnosis.json)与[文件SHA](receipt.json)。原日志、各库角路径、数据库及授权模型留在该服务器目录。大文件不搬回本机。开发检查工具仅在本地archives，不进入分支。main保持d40b217，后续修复只提交xzx。

服务器原生参数测试已通过：[读回记录](native_density_option.log)显示Innovus 21.16加载原数据库后读回旧值0.75，设置新选项后读回0.85；无ECO、无保存。它只确认参数有效，不证明新实现时序通过。
