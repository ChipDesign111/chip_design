> 历史记录：内容反映记录时的项目状态，不作为现行接口或发布规范。参见 [工程文档](../../README.md)。

# 2026-10-13 GitHub 分支审查

按用户“检查所有分支，如果没问题尽量合并”的要求，审查时远端有三个分支：

| 分支 | 审查时 head | 情况 |
| --- | --- | --- |
| main | c4804bde9f0405563b159079c13f3ce63f00ef12 | PR #2 模型已合入，已有 CI 成功 |
| codex/lab3-platform-npu | 9b23d3f41030da65c3a559bdf88c2f70bddfb345 | PR #1，外围/V1；与模型提交有三处文档冲突 |
| codex/tiled-mlp-pipeline | 72731fa4bca870a950446bd8b423588816f0476c | PR #3，基于 #1；tiled RTL/SoC/CI 已通过 |

不存在仍待处理的 feat/har-mlp-baseline 远端分支；其 PR #2 已合并。没有删除分支或强制覆盖远端历史。

冲突为 README.md、docs/numerics.md、docs/spec.md。将 main 合入 tiled 分支时保留两边设计/模型内容，修正旧“尚无实现/没有模型”状态，采用 UCI 的 3=坐、4=站编号。原权重、量化参数和训练文件保持原字节，外围 90 文件 SHA 不变。

确认模型 MULT=1064/SHIFT=20 与现有 RTL 兼容；没有为适应模型改动硬件或改原测试。补充真实模型全测试集/CPU 测试及 CI 小样本。算术参考、NumPy 独立结果、RTL、真实 CPU 互相核对，结果见 [real-model.md](../../../reports/real-model.md)。

合并顺序：先将通过检查的 PR #3 合入其基础分支，再将 PR #1 合入 main，使 main 同时包含原模型与最新版硬件。使用正常 merge，保留来源与历史；每次合并使用预期 head SHA 防止混入并发更新，并检查 CI 与合并状态。最终状态以 [PR #1](https://github.com/ChipDesign111/chip_design/pull/1)、[PR #3](https://github.com/ChipDesign111/chip_design/pull/3) 的 GitHub 记录为准。

评审保留限制：原模型按测试集选最佳 checkpoint；坐/站混淆明显。当前无正式识别准确率门槛，不将这类算法限制当成硬件错误或伪造精度提升。FPGA/ASIC 和物理 PPA 仍待验证。
