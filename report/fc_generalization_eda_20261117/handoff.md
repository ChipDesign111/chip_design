# 本轮任务已完成

用户授权的文件整理、临时脚本清理、FC通用化及PyTorch部署的更新后完整EDA验证和面积分析已完成。先读README.md和final_result.json；没有仍在运行的本轮重任务。

- 工作树：C:/Users/zixiang/OneDrive/Desktop/advanced_chip_study/tmp/main-input-window-fix；分支feat/pytorch-soc-compiler。
- 实现/TT冻结源码ee203a3；Lab5填充源码febec45。两者硬件/EDA源仅eda/server/config/lab5.json一项变化：普通M6大Dummy间距1.5→1.2µm。原始DRC阈值与源规则SHA不变。
- 物理：/home/s2400011041/Desktop/fullstack_chipdesign/uploads/20261117_094344_ee203a3。
- TT：/home/s2400011041/Desktop/fullstack_chipdesign/uploads/20261117_103549_postsim_vcs_tt_ee203a3。
- 最终Lab5：/home/s2400011041/Desktop/fullstack_chipdesign/uploads/20261117_105211_lab5_febec45。
- 本地物理/TT：工作区lab5/fc_generalization_no_auto_gating_20261117；最终Lab5：lab5/fc_generalization_m6_fill_20261117。
- 原完整pipeline因M6密度失败退出1，原pipeline.json不改写；随后正式pipeline --only lab5绑定同一物理输入并通过，session5931退出0。最终汇总明确记录接续，不冒充从新源码又综合了一遍。

635项实现SHA核验；19例功能/18SDF所有阶段时序违规0，回标/缺失/截零0；同DB半周期STA全正；Lab5必需检查全过。原始SoC2700/硬件2695拍不变。Cell Area2.252109mm²，Density82.746%，TT Setup/Hold+0.100/+0.001ns，Hold只有1ps。含PAD实现边界3.795639mm²、SealRing包络3.916441mm²分开报告。约0.0487mm²是85%全局面积预算余量，不能保证新算子可闭合。

全局insert_automatic_clock_gating=false，保留library_enable、原生组合库选择、20ns和原验收标准。CLK/复位激励、RTL/test未变；完整RTL回归复用前逐项核对120个源SHA。没有新增板测、功耗、IR/EM、全PVT/SI或填充后RC抽取。课程DRC/ERC残项及既有私有PAD补片均在最终报告中说明。

42项约323MB缓存/一次性文件已清理，后续又清一个语法缓存和两份服务器probe脚本。其他用户工作树、正式依赖、冻结work和原始证据保留。不要重复启动已完成任务或覆盖历史失败目录。

6小时单次接续已执行；完成后移除该单次任务，避免继续触发。
