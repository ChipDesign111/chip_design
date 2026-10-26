# 2026-10-26 后仿与实现结果

工艺角：TSMC180，TT，1.8 V，25 °C。以下文件来自同一版最终网表、SDF 和实现结果；原始大体积网表、SDF、VCS 可执行文件和编译数据库未提交。

## 关键结果

| 项目 | 结果 | 单位/说明 |
| --- | ---: | --- |
| 总面积（综合报告 Cell+Net） | 2,552,370.657 | library area unit；Cell 1,894,546.189，Net 657,824.468 |
| 单元面积 | 1,894,546.189 | library area unit |
| 综合实例数 | 58,635 | leaf instances |
| 后布线 Setup WNS | +0.226 | ns |
| 后布线 Setup TNS / 违例路径 | 0.000 / 0 | ns / paths |
| 后布线 Hold WNS | +0.019 | ns |
| 后布线 Hold TNS / 违例路径 | 0.000 / 0 | ns / paths |
| 功耗（TT，1.8 V，25 °C） | 35,384.3 | µW（约 35.384 mW） |
| 功能 SDF 后仿 | PASS，3659 cycles | 已调用 `$sdf_annotate` |
| 动态 timing check（全程开启） | 14 | 发生在复位窗口 |
| 动态 timing check（正常工作窗口） | 0 | 300 ns–238502 ns |

## 文件说明

- `area/area.rpt`：Genus 面积明细。
- `power/func_tt_1p80v_25c_power.rpt`：总功耗，单位 µW。
- `power/func_tt_1p80v_25c_power_hier.rpt`：按层次划分的功耗。
- `timing/postRoute_setup.summary.txt`：Innovus 后布线 Setup Slack/TNS/违例路径。
- `timing/postRoute_hold.summary.txt`：Innovus 后布线 Hold Slack/TNS/违例路径。
- `reset_window_verification.md`：复位期间屏蔽 timing check、只观察正常工作窗口的复现实验。
- `comparison.json`、`input_sha256.txt`：窗口对照统计和输入文件校验值。

动态后仿全程日志中的 14 条 timing violation 均落在初始或最终复位阶段；正常工作窗口内功能自检通过且未报告动态 timing violation。该结论适用于本次 TT/1.8 V/25 °C 激励和当前 SDF 回标配置。
