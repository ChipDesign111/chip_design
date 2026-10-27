# 全阶段85%版本：为Hold预留空间

物理源码`c8da4549d8506cd772beaa53ce5ee65c1ae41b94`，源包SHA256 `89596aab2abba164765a780ed53eceeb36b7c1953aa86c780c9071f0357b61f9`，独立目录`/home/s2400011041/Desktop/fullstack_chipdesign/uploads/20261027_063343_c8da454`。

本轮综合完成，审计通过29/34步。工具实际使用85%优化上限，但Setup先将逻辑密度推到85.001%，随后Hold再次因达到上限停止。[日志摘录](density_excerpt.log)保留实际设置及停止原因。

为避免在固定参数下重复无效修复，操作者验证两个Innovus进程均属于该上传版本后，仅终止本轮自有任务，保留全部输入和中间结果。[停止记录](operator_stop.json)与[流水线状态](summary.json)保留原因。退出1来自主动结束，不能描述成工具自然失败；本轮也没有完成34步或通过最终验收。

停止前postCTS诊断为Setup +0.009ns，Hold −0.859ns；实际转换时间违规网络555个，扇出/电容违规0。它们属于布线前诊断，见[Setup摘要](my_soc_top_postCTS.summary.gz)和[Hold摘要](my_soc_top_postCTS_hold.summary.gz)。整颗几何面积3.7956390976mm²，不能据此宣称时序通过。

后续独立实验使用旧bcc483e失败32步数据库，只在独立analysis目录中修改内存、不保存数据库、不拼接正式结果。只将Hold修复上限设为85%时，密度81.445%→82.316%，Hold −0.829ns→+0.114ns，达到100ps要求；Setup仍有4条负路径、最差−0.019ns，实际转换时间违规917个。因此有修复空间确实有用，但还必须协调Setup和电气规则。

普通Setup/DRV上限83%、Hold上限85%的组合已经隔离执行两轮：最终密度82.955%、Hold +0.114ns，实际转换时间违规降到513个，但Setup −0.294ns、50条违规，仍不满足要求。[测量记录](optimization_trials.json)保留两次实验前后数字及原输入SHA。为解决分开修复互相影响的问题，下一步试验原生optDesign -postRoute -setup -hold联合优化。

20ns、固定核心、整颗≤3.8mm²和原时序/物理门禁保持。新的正式结果仍须独立上传后，从综合完整执行34步；上述实验不能作为新版通过证明。开发脚本与原始诊断日志留在本地archives和远端独立analysis目录，不进入分支。
