# INT22：完整 SoC SDF 后仿

物理源码 `9970d6f` 的最终网表和原 SDF 已完成 **10 组 MAXIMUM SDF + 1 组无 SDF 门级功能对照**，11/11 功能通过。后仿脚本修复提交为 `5edf6cd`，修正了训练 seed 超出 `har_uci24.json` 可用范围的问题。

## 先读哪些证据

| 文件 | 作用 |
| --- | --- |
| [analysis.json](analysis.json) | 来源、门禁、周期、复位事件和半周期 STA 汇总 |
| [audit.json](audit.json) | 原始 SDF 回标警告及逐用例时序事件分类 |
| [results.json](results.json) | 11 组功能、周期、复位相位和时序消息数 |
| [input_manifest.json](input_manifest.json) | 最终网表、原 SDF、库模型、固件和测试台 SHA |
| [sdf_max.log](sdf_max.log)、[gate_zero.log](gate_zero.log) | 基础 SDF 和无 SDF 对照完整日志 |
| [sdf.log](sdf.log) | SDF 回标原文与警告类别 |
| [SRAM输入Setup](sram_timing/sram_input_setup.log)、[Hold](sram_timing/sram_input_hold.log) | 输入寄存器到宏的下降沿检查 |
| [SRAM输出Setup](sram_timing/sram_output_setup.log)、[Hold](sram_timing/sram_output_hold.log) | 宏下降沿到接收寄存器上升沿的检查 |
| [时钟报告](sram_timing/clocks.log) | 传播后的 sys_clk 20 ns 正负边沿 |
| [review.tar.gz](review.tar.gz)、[清单](review_manifest.json) | 56 份小型原始日志、命令和报告的逐文件校验归档 |

完整大网表、SDF、库模型、simv 和编译数据库保留服务器，不进入 Git。

## 功能矩阵

| 用例 | 数据 | 复位相位 |
| --- | --- | ---: |
| `sdf_max` | seed 10000，训练输入 0..3 | 2000 ps |
| `sdf_firmware_10001` | 训练输入 4..7 | 1650 ps |
| `sdf_firmware_10002` | 训练输入 8..11 | 3050 ps |
| `sdf_firmware_10003` | 训练输入 12..15 | 4450 ps |
| `sdf_firmware_10004` | 训练输入 16..19 | 5850 ps |
| `sdf_firmware_10005` | 训练输入 20..23 | 7250 ps |
| `sdf_firmware_1` | seed 1，随机 batch=2 | 250 ps |
| `sdf_firmware_3` | seed 3，随机 batch=4 | 8650 ps |
| `sdf_firmware_5` | seed 5，随机 batch=2，INT22 bias 极值 | 10050 ps |
| `sdf_firmware_7` | seed 7，随机 batch=2 | 11450 ps |
| `gate_zero` | seed 10000 | 2000 ps，无 SDF |

训练六组覆盖 `har_uci24.json` 全部 24 条输入。

## 功能检查

每例通过 Debug SBA 请求边界加载完整 2048 字镜像，实际经过 AXI 和 Boot RAM：

- 无镜像、部分镜像、错误提交密钥和未显式提交时 CPU 不启动；
- CPU 启动后通过 MMIO 驱动 NPU；
- 逐值比较全部 hidden、六个 score 和 class；
- 检查成功一批加载 64 个逻辑 tile；
- 检查 FC1/FC2 ISSUE 周期为 `batch×64` 和 `batch×16`；
- 检查 DMA 读/写与 MAC 实际重叠；
- 工作完成后从 SRAM 宏真实写入观察 PASS/FAIL 标志；
- 最终复位后检查 boot 许可撤销和 SRAM `CEN=1`。

代表性结果：

| 类型 | CPU cycles | NPU cycles | DMA/MAC overlap | 读重叠 | 写重叠 |
| --- | ---: | ---: | ---: | ---: | ---: |
| batch=4 SDF | 6370 | 975 | 279 | 278 | 278 |
| batch=2 SDF | 4258 | 880 | 140 | 140 | 139 |
| batch=4 无SDF | 6369 | 975 | 279 | 278 | 278 |

## SDF 门禁

```text
annotation_errors                       0
missing_instances                       0
unmatched_timing_checks                 0
binding_complete_for_instances_checks  true
active_window_dynamic_timing_clean      true
final_reset_timing_events               0
```

每个 SDF 用例有 108 条初始复位阶段事件，未进入工作窗口或最终复位阶段，没有关闭消息或 notifier。警告类别保留：

```text
SDFCOM_UHICD  1
SDFCOM_IWSBA 1463
SDFCOM_SWC   3476
SDFCOM_ANIOD    1
SDFCOM_NIOD    10
```

`SDFCOM_NIOD=10` 表示 10 条负 IOPATH 被 VCS 截为零。IWSBA/SWC 等对应连接仍回标。不能把该结果称为无损负延时或完整多 PVT 签核。

## SRAM 半周期 STA

只读加载同一 step34 数据库，不执行 ECO，不保存设计。对 SRAM 48 个输入引脚和 32 个输出引脚，每类列出 20 条最差路径：

| 检查 | 最差 Slack | 路径数 | 结果 |
| --- | ---: | ---: | --- |
| 输入 Setup | +6.222 ns | 20 | 全部 MET |
| 输入 Hold | +10.061 ns | 20 | 全部 MET |
| 输出 Setup | +2.685 ns | 20 | 全部 MET |
| 输出 Hold | +11.524 ns | 20 | 全部 MET |

时钟报告确认 `sys_clk` 为传播时钟、周期 20 ns、正边沿 0 ns、负边沿 10 ns；没有创建无关生成时钟或增加 false path。

## 来源与范围

```text
物理源码：9970d6f
后仿脚本：5edf6cd
物理 upload：20261103_int22_9970d6f
后仿 upload：20261104_191006_postsim_5edf6cd
SDF SHA-256：f97cd4aeed976e458c7e01f04369503ad7f3c6815f0886e4388d785200e171eb
回传包 SHA-256：54117accf66d58f285c5cecdc864a00d89a15edc4e297c42957e0ffccba14973
```

本结果覆盖单 TT、1.8 V、25 °C、MAXIMUM SDF、有限训练/随机激励和 9 个复位相位。未执行正式形式等价、独立 foundry DRC/LVS、多 PVT、IR/EM/ESD 或活动功耗重估。
