# RTL 与 GitHub / XLab 后仿核对报告（2026-10-29）

## 版本

- GitHub：`ChipDesign111/chip_design`，`main`，`b587712427c7b5460b8a345febcfea6dec9b5a21`
- XLab 物理输入：`/home/s2400012831/Desktop/fullstack_chipdesign/uploads/20261029_43f5e38_sram_reset`
- XLab 后仿输入清单：`input_manifest.json`
- XLab 复跑目录：`/home/s2400012831/Desktop/fullstack_chipdesign/uploads/20261029_171412_postsim_2714f61/postsim/postsim_retry_20261029c`

## 一致性结果

逐字节比较本地工作区和 GitHub `main`：

- RTL：`rtl/axi`、`rtl/dma`、`rtl/memory`、`rtl/npu`、`rtl/soc` 以及 `rtl/filelist.f`、`rtl/manifest.json` 均一致。
- 关键 EDA/验证文件：`eda/postsim.py`、`eda/server/postsim/run.py`、`report/reset_fix.md`、`report/functional_validation.json` 均一致。
- GitHub 中本地也存在的文件：349 个一致，2 个 FPGA 工程文件存在差异：`fpga/final_project/final_project.xpr` 和 `fpga/final_project/final_project.srcs/sources_1/ip/clk_wiz_0/clk_wiz_0.xci`。另有 GitHub 的 `fpga/TEST_REPORT.md` 本地缺失。
- 当前工作区的许多 `M/D/??` 状态是相对本地旧提交的工作树状态；按文件内容与远端 `main` 比较，RTL 本身没有内容差异。

## XLab 新一轮 SDF 后仿

同一份最新布局后网表和 SDF，重新执行 16 组 MAXIMUM SDF 后仿，复位断言相位覆盖 0.25 ns–19.85 ns，另有 2 ns 基准组：

- 功能通过：`16/16`
- 动态 timing violation 消息总数：`111`，全部出现在复位/初始化检查窗口；功能工作窗口仍完成。
- 每组：`npu_cycles=1035`、`dma_mac_overlap=93`、`read_overlap=62`、`write_overlap=93`
- 每组均出现 `FUNCTIONAL_PASS` 和 `POSTSIM_DONE`。

`gate_zero` 无 SDF 对照在零延迟门级网表下发生 CPU numeric self-check failed。它是用于对照的零延迟控制，不是 SDF 后仿；本轮不把它计入 16 组 SDF 通过率，也不据此否定 SDF 结果。

## 本地证据

- `results.json`：16 组复跑统计。
- `input_manifest.json`：实际网表、SDF、标准单元、IO、SRAM 模型、测试台和固件 SHA-256。
- `logs/`：16 组仿真日志。

这轮结果仍属于单一 TT/1.8 V/25 °C、MAXIMUM SDF 和有限固件/复位相位覆盖；不替代多 PVT、独立晶圆厂签核、IR/EM/ESD 或形式等价验证。
