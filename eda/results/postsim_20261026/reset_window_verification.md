# 复位窗口 timing check 对照复仿

## 结果

同一个 VCS 可执行文件、固件和 SDF，分别执行两次完整 SoC 后仿：

| 运行 | timing check 控制 | 动态违例 | 功能自检 | 退出码 |
| --- | --- | ---: | --- | ---: |
| control | 全程启用消息与 notifier | 14 | SDF_POSTSIM PASS cycles=3659 | 0 |
| reset_window | 只在初始复位稳定窗口和最终复位阶段关闭消息与 notifier | 0（启用窗口内） | SDF_POSTSIM PASS cycles=3659 | 0 |

时序检查启用窗口是 **300 ns 至 238502 ns（238.502 µs）**。它包含固件加载、启动保护测试、CPU 启动、DMA 与 INT8 自检。两次运行的结束时间均为 238900 ns。没有重新综合、改动网表、修改时钟周期、添加 false path 或使用全程 +notimingchecks。

## 屏蔽范围与证据

使用 VCS UCLI 原生 `tcheck` 命令，递归控制 `tb_soc.dut`：`-msg` 控制报告，`-xgen` 控制 notifier。关闭二者意味着这些窗口中的违例不会报告或传播 X，并不是电路中的违例被修好了。

1. 0–300 ns：屏蔽初始上电、复位及稳定等待窗口。外部复位在 82 ns 释放；300 ns 时查询到 `rst_n=1`、`ndmreset_n=1`、`boot_ready=0`、`load_req=0`。
2. 300 ns：重新启用所有层次的消息与 notifier。日志对 CSR 门控单元的查询显示 SETUP/WIDTH 检查的 msg/xgen 均为 ON。
3. 300–238502 ns：保持检查开启，执行加载和完整功能自检，没有 Timing violation。
4. 238502 ns：在测试平台最终 `rst_n` 下降沿暂停，关闭检查，再继续完成复位断言自检和 `$finish`。

原始 14 条在全程启用对照中逐条复现：前 13 条约在 11.216–11.673 ns，此时外部复位尚未释放；最后一条在 238511.215 ns，即最终复位断言后约 9.215 ns。正常工作窗口内未出现这 14 条中的任何一条。

## 如何理解

这组对照支持“原有 14 条动态 setup 违例集中在初始/最终复位阶段”的判断，当前测试的正常工作窗口未报告动态 timing violation。它不能证明复位阶段的真实电气行为无风险，也没有单独证明每个违例的电路根因。

沿用原有 VCS 编译配置与 SDF 回标，原先负 SETUPHOLD/RECREM 被置零、removal 检查映射等问题尚未修复；本次并未重新编译以启用 +neg_tchk、库 NTC 分支等。因而“0 条”仅适用于目前实际生效的回标与检查，不代表全部 SDF 检查均正确回标，也不代表完整签核通过。

分析条件沿用原有 TT、1.8 V、25°C 和 MAXIMUM SDF 选择，功能覆盖沿用当前 SoC 固件测试；不能由此外推所有激励或其他工艺角。

## 文件与复现

- `control/control.log`：全程检查对照日志，14 条违例。
- `reset_window/reset_window.log`：窗口控制日志，包含启用状态、窗口边界和功能 PASS。
- `control/control.ucli`、`reset_window/reset_window.ucli`：精确控制脚本。
- `comparison.json`：计数和退出码。
- `input_sha256.txt`：远程实际使用的 simv、SDF、固件、测试平台、网表的 SHA-256。

远程工作目录：

```text
/home/s2400012831/Desktop/fullstack_chipdesign/uploads/postsim_20261026_035946e/postsim_run/reset_window_control
/home/s2400012831/Desktop/fullstack_chipdesign/uploads/postsim_20261026_035946e/postsim_run/reset_window_check
```

这两个目录通过符号链接使用原始 simv、simv.daidir、firmware.hex、my_soc_top_tt_io.sdf。在对应目录内分别运行：

```bash
./simv -ucli -do control.ucli -l control.log
./simv -ucli -do reset_window.ucli -l reset_window.log
```
