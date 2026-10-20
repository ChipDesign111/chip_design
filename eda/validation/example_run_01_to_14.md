> 实际运行示例：本工程复用同源、同综合设置、同库身份的已完成综合网表，随后实际执行后端01–14并验证跨进程恢复。没有在这个目标工程重跑Genus；15–34未执行。具体证据与快照差异见[验证说明](README.md)和[pnr_smoke.json](pnr_smoke.json)。原运行快照第08步文字仍使用“保存内部网络对象”的简写，下面实际Tcl已使用稳定内部引脚；最新讲解见[操作指南](../docs/操作指南.md)。

# 本轮EDA运行记录

工程：`/home/s2400011041/eda_validation/20261020_eda_9d2c7f/work_padfix`

配置与源身份：见input_manifest.json、source.json和preparation.json。

功能证据已附：True。EDA流程不等于功能回归或独立工艺签核。

## Genus输入、展开、综合与交接

输入清单有77份RTL；主存选择与源身份见preparation.json。

**G1：完整综合已包含展开，未另跑独立展开检查。**

**G2 综合执行：**

```json
{
  "commands_completed": true,
  "reused_validated_fixture": true,
  "fresh_Genus_executed_here": false,
  "reference_work": "/home/s2400011041/eda_validation/20261020_eda_9d2c7f/work03",
  "scope": "Reused mapped synthesis fixture for current-controller PNR smoke test, NOT a fresh Genus run in this target work"
}
```

**G3 综合面积与映射结果：**

```json
{
  "cell_count": 165606,
  "cell_area_um2": 4672791.309,
  "net_area_um2": 1788325.962,
  "latch_area_um2": 0.0,
  "memory_area_um2": 401443.591,
  "report": "/home/s2400011041/eda_validation/20261020_eda_9d2c7f/work_padfix/syn/my_soc_top/reports/area/area.rpt",
  "mapped_design": {
    "native_main_srams": 1,
    "mapped_leaf_instances": 165606,
    "all_leaf_types_have_library_models": true,
    "npu_dma_area_hierarchy_present": true,
    "latch_area_um2": 0
  }
}
```

**G4 新面积与后端规划：**

```json
{
  "cell_count": 165606,
  "cell_area_um2": 4672791.309,
  "net_area_um2": 1788325.962,
  "latch_area_um2": 0.0,
  "memory_area_um2": 401443.591,
  "report": "/home/s2400011041/eda_validation/20261020_eda_9d2c7f/work_padfix/syn/my_soc_top/reports/area/area.rpt",
  "standard_cell_area_estimate_um2": 4271347.71825,
  "reserved_macro_halo_um2": 470626.73075000005,
  "target_utilization": 0.5,
  "core_size_um": 3100,
  "planning_only_not_timing_or_IR_proof": true
}
```

## 01 导入新门级设计

**做什么：** 读入新版SoC网表、库外形与时间模型，并查找唯一主SRAM。

**为什么：** 网表只写连接，库资料才给出实际器件；先排除旧网表、缺模型和选错宏。

**预期效果：** 设计名my_soc_top，主SRAM恰好一个，记录综合后真实实例路径。

**关键参数：** 顶层固定为my_soc_top，宏型号固定RA1SHD_2048x32M8；实例名从当前数据库查询，不照搬旧层次路径。

**本轮实际执行片段：** 下列是运行时保存的Tcl正文；宏路径已解析，其他变量结合配置与日志阅读。

`001_01_tcl.tcl`

```tcl
# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
dbGet top.name
dbGet top.insts.cell.name RA1SHD_2048x32M8

dbGet [dbGet top.insts.cell.name RA1SHD_2048x32M8 -p2].name
dbGet head.sites.name
```

**本轮结果：** 步骤命令与对应自动检查已通过；详见`step_01.json`，独立验收范围以该JSON为准。

```json
{
  "step": 1,
  "commands_completed": true,
  "input_manifest_sha256": "702782c4bfff5f9afacfb9e9aa8060f390022b8b6792fff87aff1d7a6f6a087c",
  "automatic_checks": {
    "native_sram_resolved": true
  },
  "scope": "Only the listed automatic checks are asserted. Tcl guards also check object counts, IO geometry and halo. Not complete signoff."
}
```

## 02 确定核心与裸片尺寸

**做什么：** 根据新综合面积和目标放置密度估算核心，再由工具建立合法行网格。

**为什么：** NPU权重和乘法逻辑增加面积，不能直接复用原1500尺寸；网格吸附后坐标也会变化。

**预期效果：** 生成floorplan_plan.json与geometry.json，后续外围统一使用实际Die尺寸。

**关键参数：** core_size_um为空时根据新Cell Area自动估算；target_utilization默认0.5，外围边距150 um，core7T提供合法行网格。工具实际Die尺寸用于所有后续坐标。

**本轮实际执行片段：** 下列是运行时保存的Tcl正文；宏路径已解析，其他变量结合配置与日志阅读。

`001_02_tcl.tcl`

```tcl
# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
floorPlan -coreMarginsBy die -site core7T -s $eda_core_size $eda_core_size 150 150 150 150
```

**本轮结果：** 步骤命令与对应自动检查已通过；详见`step_02.json`，独立验收范围以该JSON为准。

```json
{
  "step": 2,
  "commands_completed": true,
  "input_manifest_sha256": "702782c4bfff5f9afacfb9e9aa8060f390022b8b6792fff87aff1d7a6f6a087c",
  "automatic_checks": {
    "geometry": {
      "die_um": [
        0.0,
        0.0,
        3400.32,
        3400.32
      ],
      "signal_pads": [
        {
          "port": "clk_i",
          "pad": "clk",
          "direction": "input",
          "side": "N",
          "offset_um": 300
        },
        {
          "port": "rst_ni",
          "pad": "rst_n",
          "direction": "input",
          "side": "N",
          "offset_um": 1400
        },
        {
          "port": "tck_i",
          "pad": "tck",
          "direction": "input",
          "side": "S",
          "offset_um": 250
        },
        {
          "port": "tms_i",
          "pad": "tms",
          "direction": "input",
          "side": "S",
          "offset_um": 450
        },
        {
          "port": "td_i",
          "pad": "tdi",
          "direction": "input",
          "side": "S",
          "offset_um": 1400
        },
        {
          "port": "td_o",
          "pad": "tdo",
          "direction": "output",
          "side": "S",
          "offset_um": 1600
        }
      ],
      "power_slots": [
        {
          "suffix": "vss_1",
          "master": "PVSS1CDG",
          "offset_um": 600
        },
        {
          "suffix": "vss_2",
          "master": "PVSS1CDG",
          "offset_um": 700
        },
        {
          "suffix": "vssio",
          "master": "PVSS2CDG",
          "offset_um": 800
        },
        {
          "suffix": "vdd_1",
          "master": "PVDD1CDG",
          "offset_um": 900
        },
        {
          "suffix": "vdd_2",
          "master": "PVDD1CDG",
          "offset_um": 1000
        },
        {
          "suffix": "vddio",
          "master": "PVDD2CDG",
          "offset_um": 1100
        },
        {
          "suffix": "poc",
          "master": "PVDD2POC",
          "offset_um": 1200
        }
      ],
      "pin_rectangles_um": {
        "clk_i": [
          310,
          3397.92,
          320,
          3398.92
        ],
        "rst_ni": [
          1410,
          3397.92,
          1420,
          3398.92
        ],
        "tck_i": [
          260,
          1,
          270,
          2
        ],
        "tms_i": [
          460,
          1,
          470,
          2
        ],
        "td_i": [
          1410,
          1,
          1420,
          2
        ],
        "td_o": [
          1610,
          1,
          1620,
          2
        ],
        "VDD": [
          910,
          3397.92,
          920,
          3398.92
        ],
        "VSS": [
          610,
          3397.92,
          620,
          3398.92
        ],
        "VDDPST": [
          1110,
          3397.92,
          1120,
          3398.92
        ],
        "VSSPST": [
          810,
          3397.92,
          820,
          3398.92
        ]
      },
      "main_macro_xy_um": [
        250,
        650
      ],
      "generated_from_measured_database_geometry": true
    }
  },
  "scope": "Only the listed automatic checks are asserted. Tcl guards also check object counts, IO geometry and halo. Not complete signoff."
}
```

## 03 识别SRAM硬宏

**做什么：** 查询宏的型号、实例名、尺寸和分类。

**为什么：** 型号是库里的模板，实例是本设计使用一次；后续放置必须找对具体实例。

**预期效果：** 确认RA1SHD_2048x32M8并保存查询结果，尚不改变位置。

**关键参数：** `cell.size`是LEF定义的物理大小；`baseClass=block`区分硬宏与标准单元。RTL中预计为i_mainmem/i_sram/i_macro；综合可能改名，以本步数据库查询的唯一实例为准。

**本轮实际执行片段：** 下列是运行时保存的Tcl正文；宏路径已解析，其他变量结合配置与日志阅读。

`001_03_tcl.tcl`

```tcl
# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
dbGet [dbGet top.insts.cell.name RA1SHD_2048x32M8 -p2].name
dbGet [dbGet top.insts.cell.name RA1SHD_2048x32M8 -p2].cell.size
dbGet [dbGet top.insts.cell.name RA1SHD_2048x32M8 -p2].cell.baseClass
```

**本轮结果：** 步骤命令与对应自动检查已通过；详见`step_03.json`，独立验收范围以该JSON为准。

```json
{
  "step": 3,
  "commands_completed": true,
  "input_manifest_sha256": "702782c4bfff5f9afacfb9e9aa8060f390022b8b6792fff87aff1d7a6f6a087c",
  "automatic_checks": {},
  "scope": "Only the listed automatic checks are asserted. Tcl guards also check object counts, IO geometry and halo. Not complete signoff."
}
```

## 04 保存插PAD之前的恢复点

**做什么：** 核对六个逻辑信号端口、确认尚无PAD，保存prePad。

**为什么：** 接下来要改变端口与内部网络关系，出错时可以恢复到清楚的基线。

**预期效果：** 六路接口存在但六个PAD还未摆放；本步不是布局动作。

**关键参数：** `saveDesign`保存数据库及配套.enc.dat；保存文件名不是验收结论。每边为2核心VDD、2核心VSS、1IO VDD、1IO VSS、1POC。

**本轮实际执行片段：** 下列是运行时保存的Tcl正文；宏路径已解析，其他变量结合配置与日志阅读。

`001_04_tcl.tcl`

```tcl
# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
dbGet top.terms.name
set prior_pads [dbGet -e top.insts.cell.baseClass pad -p2]
if {[llength $prior_pads] != 0} {error "Unexpected existing PAD"}
saveDesign ../my_soc_top/backup/my_soc_top_prePad.enc
if {[lsort [dbGet top.terms.name]] ne [lsort {clk_i rst_ni tck_i tms_i td_i td_o}]} {error "Unexpected top-level signal ports"}
```

**本轮结果：** 步骤命令与对应自动检查已通过；详见`step_04.json`，独立验收范围以该JSON为准。

```json
{
  "step": 4,
  "commands_completed": true,
  "input_manifest_sha256": "702782c4bfff5f9afacfb9e9aa8060f390022b8b6792fff87aff1d7a6f6a087c",
  "automatic_checks": {},
  "scope": "Only the listed automatic checks are asserted. Tcl guards also check object counts, IO geometry and halo. Not complete signoff."
}
```

## 05 摆放四角单元

**做什么：** 在实际裸片四角放置PCORNER并固定方向。

**为什么：** 外围直线单元里的电源轨需要在角部转接，位置和方向都影响连通。

**预期效果：** 四角均fixed且方向正确；这些不是需要计算功能的信号单元。

**关键参数：** 角块115×115 um；东/北边起点分别是实际宽/高减115，方向R0/MY/MX/R180必须与边别对应。

**本轮实际执行片段：** 下列是运行时保存的Tcl正文；宏路径已解析，其他变量结合配置与日志阅读。

`001_05_tcl.tcl`

```tcl
# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
addInst -physical -cell PCORNER -inst corner_bottom_left -loc {0.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PCORNER -inst corner_bottom_right -loc {3285.320000 0.000000} -ori MY -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PCORNER -inst corner_top_left -loc {0.000000 3285.320000} -ori MX -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PCORNER -inst corner_top_right -loc {3285.320000 3285.320000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
if {[dbGet [dbGet top.insts.name corner_bottom_left -p].pStatus] ne "fixed" || [dbGet [dbGet top.insts.name corner_bottom_left -p].orient] ne "R0"} {error "Corner placement failed"}
if {[dbGet [dbGet top.insts.name corner_bottom_right -p].pStatus] ne "fixed" || [dbGet [dbGet top.insts.name corner_bottom_right -p].orient] ne "MY"} {error "Corner placement failed"}
if {[dbGet [dbGet top.insts.name corner_top_left -p].pStatus] ne "fixed" || [dbGet [dbGet top.insts.name corner_top_left -p].orient] ne "MX"} {error "Corner placement failed"}
if {[dbGet [dbGet top.insts.name corner_top_right -p].pStatus] ne "fixed" || [dbGet [dbGet top.insts.name corner_top_right -p].orient] ne "R180"} {error "Corner placement failed"}
```

**本轮结果：** 步骤命令与对应自动检查已通过；详见`step_05.json`，独立验收范围以该JSON为准。

```json
{
  "step": 5,
  "commands_completed": true,
  "input_manifest_sha256": "702782c4bfff5f9afacfb9e9aa8060f390022b8b6792fff87aff1d7a6f6a087c",
  "automatic_checks": {},
  "scope": "Only the listed automatic checks are asserted. Tcl guards also check object counts, IO geometry and halo. Not complete signoff."
}
```

## 06 把IO时间模型纳入分析

**做什么：** 在核心与SRAM时间库上增加IO库，并激活func_tt_io分析视图。

**为什么：** 信号经过PAD也需要时间；只放几何而没启用时间模型会漏算延时。

**预期效果：** Setup/Hold使用包含核心、SRAM与IO的同一单TT视图。

**关键参数：** library_set描述单元延时库，rc_corner描述导线RC，delay_corner把两者组合，analysis_view再加入constraint_mode。本流程明确-si_enabled false。

**本轮实际执行片段：** 下列是运行时保存的Tcl正文；宏路径已解析，其他变量结合配置与日志阅读。

`001_06_tcl.tcl`

```tcl
# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
create_library_set -name lib_tt_io -timing [concat $tt_1p80v_25c_libs [list ${io_lib}tc.lib]]
create_delay_corner -name delay_tt_io -library_set lib_tt_io -rc_corner rc_tt_1p80v_25c -si_enabled false
create_analysis_view -name func_tt_io -constraint_mode func -delay_corner delay_tt_io
set_analysis_view -setup {func_tt_io} -hold {func_tt_io}
all_analysis_views -type setup
all_analysis_views -type hold
report_analysis_views
```

**本轮结果：** 步骤命令与对应自动检查已通过；详见`step_06.json`，独立验收范围以该JSON为准。

```json
{
  "step": 6,
  "commands_completed": true,
  "input_manifest_sha256": "702782c4bfff5f9afacfb9e9aa8060f390022b8b6792fff87aff1d7a6f6a087c",
  "automatic_checks": {},
  "scope": "Only the listed automatic checks are asserted. Tcl guards also check object counts, IO geometry and halo. Not complete signoff."
}
```

## 07 摆放六个信号PAD

**做什么：** 按io_plan.json把clk/rst放北边，四路JTAG放南边。

**为什么：** 外部接口需要真实输入输出电路，不能把RTL端口名当作完整外围。

**预期效果：** 六个PDDW0204CDG实例都有位置且fixed，但下一步才接内部信号。

**关键参数：** 每个PAD60×115 um，北边R180、南边R0。沿边偏移取io_plan.json；北边y=实际高度−115，不能沿用旧1685.4。

**本轮实际执行片段：** 下列是运行时保存的Tcl正文；宏路径已解析，其他变量结合配置与日志阅读。

`001_07_tcl.tcl`

```tcl
# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
addInst -cell PDDW0204CDG -inst i_pad_clk -loc {300.000000 3285.320000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PDDW0204CDG -inst i_pad_rst_n -loc {1400.000000 3285.320000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PDDW0204CDG -inst i_pad_tck -loc {250.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PDDW0204CDG -inst i_pad_tms -loc {450.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PDDW0204CDG -inst i_pad_tdi -loc {1400.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PDDW0204CDG -inst i_pad_tdo -loc {1600.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
if {[llength [dbGet -e top.insts.cell.name PDDW0204CDG -p2]] != 6} {error "Signal PAD count mismatch"}
```

**本轮结果：** 步骤命令与对应自动检查已通过；详见`step_07.json`，独立验收范围以该JSON为准。

```json
{
  "step": 7,
  "commands_completed": true,
  "input_manifest_sha256": "702782c4bfff5f9afacfb9e9aa8060f390022b8b6792fff87aff1d7a6f6a087c",
  "automatic_checks": {},
  "scope": "Only the listed automatic checks are asserted. Tcl guards also check object counts, IO geometry and halo. Not complete signoff."
}
```

## 08 连接PAD与核心

**做什么：** 先保存内部网络对象，再把顶层端口转到外侧网络，并连接PAD/C/I及控制脚。

**为什么：** 输入应先经过接收电路，输出应经过发送电路；原内部端点必须一个不漏。

**预期效果：** 导出改接网表并与综合网表比较，六路外侧只连接各自PAD。

**关键参数：** 输入PAD：OEN=1关闭输出，IE=1开启输入，I/PE/DS=0。输出PAD：I接核心输出，OEN=0开启输出，IE/PE/DS=0。PAD是外侧端，C是接收输出，I是发送输入，不能混接。

**本轮实际执行片段：** 下列是运行时保存的Tcl正文；宏路径已解析，其他变量结合配置与日志阅读。

`001_08_tcl.tcl`

```tcl
# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
set eda_term [dbGet top.terms.name clk_i -p]
set eda_core_object [dbGet $eda_term.net]
set eda_core_anchor [lindex [dbGet -e $eda_core_object.instTerms] 0]
if {$eda_core_anchor in {{} 0x0}} {error "Signal has no internal pin anchor"}
addNet clk_i_pad
detachModulePort - clk_i
attachModulePort - clk_i clk_i_pad
set eda_core_net [dbGet $eda_core_anchor.net.name]
set eda_ext_net [dbGet [dbGet top.terms.name clk_i -p].net.name]
if {$eda_core_net in {{} 0x0} || $eda_ext_net in {{} 0x0} || $eda_core_net eq $eda_ext_net} {error "Invalid core/PAD split"}
attachTerm i_pad_clk PAD $eda_ext_net
attachTerm i_pad_clk C $eda_core_net
attachTerm i_pad_clk OEN 1'b1
attachTerm i_pad_clk IE 1'b1
attachTerm i_pad_clk PE 1'b0
attachTerm i_pad_clk DS 1'b0
attachTerm i_pad_clk I 1'b0
set eda_term [dbGet top.terms.name rst_ni -p]
set eda_core_object [dbGet $eda_term.net]
set eda_core_anchor [lindex [dbGet -e $eda_core_object.instTerms] 0]
if {$eda_core_anchor in {{} 0x0}} {error "Signal has no internal pin anchor"}
addNet rst_ni_pad
detachModulePort - rst_ni
attachModulePort - rst_ni rst_ni_pad
set eda_core_net [dbGet $eda_core_anchor.net.name]
set eda_ext_net [dbGet [dbGet top.terms.name rst_ni -p].net.name]
if {$eda_core_net in {{} 0x0} || $eda_ext_net in {{} 0x0} || $eda_core_net eq $eda_ext_net} {error "Invalid core/PAD split"}
attachTerm i_pad_rst_n PAD $eda_ext_net
attachTerm i_pad_rst_n C $eda_core_net
attachTerm i_pad_rst_n OEN 1'b1
attachTerm i_pad_rst_n IE 1'b1
attachTerm i_pad_rst_n PE 1'b0
attachTerm i_pad_rst_n DS 1'b0
attachTerm i_pad_rst_n I 1'b0
set eda_term [dbGet top.terms.name tck_i -p]
set eda_core_object [dbGet $eda_term.net]
set eda_core_anchor [lindex [dbGet -e $eda_core_object.instTerms] 0]
if {$eda_core_anchor in {{} 0x0}} {error "Signal has no internal pin anchor"}
addNet tck_i_pad
detachModulePort - tck_i
attachModulePort - tck_i tck_i_pad
set eda_core_net [dbGet $eda_core_anchor.net.name]
set eda_ext_net [dbGet [dbGet top.terms.name tck_i -p].net.name]
if {$eda_core_net in {{} 0x0} || $eda_ext_net in {{} 0x0} || $eda_core_net eq $eda_ext_net} {error "Invalid core/PAD split"}
attachTerm i_pad_tck PAD $eda_ext_net
attachTerm i_pad_tck C $eda_core_net
attachTerm i_pad_tck OEN 1'b1
attachTerm i_pad_tck IE 1'b1
attachTerm i_pad_tck PE 1'b0
attachTerm i_pad_tck DS 1'b0
attachTerm i_pad_tck I 1'b0
set eda_term [dbGet top.terms.name tms_i -p]
set eda_core_object [dbGet $eda_term.net]
set eda_core_anchor [lindex [dbGet -e $eda_core_object.instTerms] 0]
if {$eda_core_anchor in {{} 0x0}} {error "Signal has no internal pin anchor"}
addNet tms_i_pad
detachModulePort - tms_i
attachModulePort - tms_i tms_i_pad
set eda_core_net [dbGet $eda_core_anchor.net.name]
set eda_ext_net [dbGet [dbGet top.terms.name tms_i -p].net.name]
if {$eda_core_net in {{} 0x0} || $eda_ext_net in {{} 0x0} || $eda_core_net eq $eda_ext_net} {error "Invalid core/PAD split"}
attachTerm i_pad_tms PAD $eda_ext_net
attachTerm i_pad_tms C $eda_core_net
attachTerm i_pad_tms OEN 1'b1
attachTerm i_pad_tms IE 1'b1
attachTerm i_pad_tms PE 1'b0
attachTerm i_pad_tms DS 1'b0
attachTerm i_pad_tms I 1'b0
set eda_term [dbGet top.terms.name td_i -p]
set eda_core_object [dbGet $eda_term.net]
set eda_core_anchor [lindex [dbGet -e $eda_core_object.instTerms] 0]
if {$eda_core_anchor in {{} 0x0}} {error "Signal has no internal pin anchor"}
addNet td_i_pad
detachModulePort - td_i
attachModulePort - td_i td_i_pad
set eda_core_net [dbGet $eda_core_anchor.net.name]
set eda_ext_net [dbGet [dbGet top.terms.name td_i -p].net.name]
if {$eda_core_net in {{} 0x0} || $eda_ext_net in {{} 0x0} || $eda_core_net eq $eda_ext_net} {error "Invalid core/PAD split"}
attachTerm i_pad_tdi PAD $eda_ext_net
attachTerm i_pad_tdi C $eda_core_net
attachTerm i_pad_tdi OEN 1'b1
attachTerm i_pad_tdi IE 1'b1
attachTerm i_pad_tdi PE 1'b0
attachTerm i_pad_tdi DS 1'b0
attachTerm i_pad_tdi I 1'b0
set eda_term [dbGet top.terms.name td_o -p]
set eda_core_object [dbGet $eda_term.net]
set eda_core_anchor [lindex [dbGet -e $eda_core_object.instTerms] 0]
if {$eda_core_anchor in {{} 0x0}} {error "Signal has no internal pin anchor"}
addNet td_o_pad
detachModulePort - td_o
attachModulePort - td_o td_o_pad
set eda_core_net [dbGet $eda_core_anchor.net.name]
set eda_ext_net [dbGet [dbGet top.terms.name td_o -p].net.name]
if {$eda_core_net in {{} 0x0} || $eda_ext_net in {{} 0x0} || $eda_core_net eq $eda_ext_net} {error "Invalid core/PAD split"}
attachTerm i_pad_tdo PAD $eda_ext_net
attachTerm i_pad_tdo I $eda_core_net
attachTerm i_pad_tdo OEN 1'b0
attachTerm i_pad_tdo IE 1'b0
attachTerm i_pad_tdo PE 1'b0
attachTerm i_pad_tdo DS 1'b0
saveNetlist ../my_soc_top/my_soc_top_io_connected.v
```

**本轮结果：** 步骤命令与对应自动检查已通过；详见`step_08.json`，独立验收范围以该JSON为准。

```json
{
  "step": 8,
  "commands_completed": true,
  "input_manifest_sha256": "702782c4bfff5f9afacfb9e9aa8060f390022b8b6792fff87aff1d7a6f6a087c",
  "automatic_checks": {
    "topology": {
      "program": "audit_io_topology.py",
      "exit_code": 0
    }
  },
  "scope": "Only the listed automatic checks are asserted. Tcl guards also check object counts, IO geometry and halo. Not complete signoff."
}
```

## 09 摆放供电与上电控制PAD

**做什么：** 四边各放七个供电/POC单元，并按实际坐标登记IO侧别。

**为什么：** 后续外围填充依赖正确侧别；核心电源和IO电源的作用与网络不能混淆。

**预期效果：** 新增28个单元，IO登记前后位置不变，角块/边别通过几何检查。

**关键参数：** 每边2个核心VDD、2个核心VSS、1个IO VDD、1个IO VSS、1个POC；默认沿边偏移600到1200 um。loadIoFile只登记指定对象，不调整Die。

**本轮实际执行片段：** 下列是运行时保存的Tcl正文；宏路径已解析，其他变量结合配置与日志阅读。

`001_09_tcl.tcl`

```tcl
# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
addInst -cell PVSS1CDG -inst i_pad_N_vss_1 -loc {600.000000 3285.320000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS1CDG -inst i_pad_N_vss_2 -loc {700.000000 3285.320000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS2CDG -inst i_pad_N_vssio -loc {800.000000 3285.320000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD1CDG -inst i_pad_N_vdd_1 -loc {900.000000 3285.320000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD1CDG -inst i_pad_N_vdd_2 -loc {1000.000000 3285.320000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD2CDG -inst i_pad_N_vddio -loc {1100.000000 3285.320000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD2POC -inst i_pad_N_poc -loc {1200.000000 3285.320000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS1CDG -inst i_pad_S_vss_1 -loc {600.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS1CDG -inst i_pad_S_vss_2 -loc {700.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS2CDG -inst i_pad_S_vssio -loc {800.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD1CDG -inst i_pad_S_vdd_1 -loc {900.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD1CDG -inst i_pad_S_vdd_2 -loc {1000.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD2CDG -inst i_pad_S_vddio -loc {1100.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD2POC -inst i_pad_S_poc -loc {1200.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS1CDG -inst i_pad_W_vss_1 -loc {0.000000 600.000000} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS1CDG -inst i_pad_W_vss_2 -loc {0.000000 700.000000} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS2CDG -inst i_pad_W_vssio -loc {0.000000 800.000000} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD1CDG -inst i_pad_W_vdd_1 -loc {0.000000 900.000000} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD1CDG -inst i_pad_W_vdd_2 -loc {0.000000 1000.000000} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD2CDG -inst i_pad_W_vddio -loc {0.000000 1100.000000} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD2POC -inst i_pad_W_poc -loc {0.000000 1200.000000} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS1CDG -inst i_pad_E_vss_1 -loc {3285.320000 600.000000} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS1CDG -inst i_pad_E_vss_2 -loc {3285.320000 700.000000} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS2CDG -inst i_pad_E_vssio -loc {3285.320000 800.000000} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD1CDG -inst i_pad_E_vdd_1 -loc {3285.320000 900.000000} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD1CDG -inst i_pad_E_vdd_2 -loc {3285.320000 1000.000000} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD2CDG -inst i_pad_E_vddio -loc {3285.320000 1100.000000} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD2POC -inst i_pad_E_poc -loc {3285.320000 1200.000000} -ori R90 -place_status fixed -dontSnapToPlacementGrid
puts "POWER_PAD_COUNT [llength [dbGet -e top.insts.name i_pad_?_*]]"
saveIoFile -locations -includeCellName ../my_soc_top/my_soc_top_io_beforeFiller.io

saveDesign ../my_soc_top/backup/my_soc_top_preIORegistration.enc
set io_die [lindex [dbGet top.fPlan.box] 0]
lassign $io_die io_dx0 io_dy0 io_dx1 io_dy1
set io_tol 0.001
set io_rows [dict create top {} bottom {} left {} right {}]
set io_corners [dict create]
set io_before [dict create]
foreach io_inst [dbGet top.insts] {
    set io_class [dbGet $io_inst.cell.baseClass]
    if {$io_class ni {pad corner}} {continue}
    set io_subclass [dbGet $io_inst.cell.subClass]
    if {[string match -nocase *spacer* $io_subclass]} {continue}
    set io_name [dbGet $io_inst.name]
    set io_cell [dbGet $io_inst.cell.name]
    if {[regexp {["\\]} "$io_name$io_cell"]} {
        error "Unsupported quote/backslash in IO name or master: $io_name"
    }
    if {[dbGet $io_inst.pStatus] ne "fixed"} {
        error "IO must be fixed before registration: $io_name"
    }
    set io_box [lindex [dbGet $io_inst.box] 0]
    lassign $io_box io_x0 io_y0 io_x1 io_y1
    set io_ori [dbGet $io_inst.orient]
    if {$io_x0 < $io_dx0-$io_tol || $io_y0 < $io_dy0-$io_tol ||
        $io_x1 > $io_dx1+$io_tol || $io_y1 > $io_dy1+$io_tol} {
        error "IO outside measured Die: $io_name"
    }
    dict set io_before $io_name [list $io_box $io_ori]
    if {$io_class eq "corner"} {
        set io_horizontal ""
        set io_vertical ""
        if {abs($io_x0-$io_dx0) < $io_tol} {set io_horizontal left}
        if {abs($io_x1-$io_dx1) < $io_tol} {set io_horizontal right}
        if {abs($io_y0-$io_dy0) < $io_tol} {set io_vertical bottom}
        if {abs($io_y1-$io_dy1) < $io_tol} {set io_vertical top}
        if {$io_horizontal eq "" || $io_vertical eq ""} {
            error "Corner does not touch a rectangle corner: $io_name"
        }
        set io_side "$io_vertical$io_horizontal"
        if {[dict exists $io_corners $io_side]} {
            error "Duplicate corner side: $io_side"
        }
        dict set io_corners $io_side [list $io_name $io_cell $io_ori]
    } else {
        set io_distances [list \
            [list [expr {abs($io_y0-$io_dy0)}] bottom] \
            [list [expr {abs($io_dy1-$io_y1)}] top] \
            [list [expr {abs($io_x0-$io_dx0)}] left] \
            [list [expr {abs($io_dx1-$io_x1)}] right]]
        set io_distances [lsort -real -index 0 $io_distances]
        set io_indent [lindex $io_distances 0 0]
        if {[lindex $io_distances 1 0]-$io_indent < $io_tol} {
            error "IO side is ambiguous from physical box: $io_name"
        }
        set io_side [lindex $io_distances 0 1]
        if {$io_side in {top bottom}} {
            set io_offset [expr {$io_x0-$io_dx0}]
        } else {
            set io_offset [expr {$io_y0-$io_dy0}]
        }
        dict lappend io_rows $io_side [list $io_offset $io_name $io_cell $io_indent $io_ori]
    }
}
if {[dict size $io_corners] != 4} {
    error "Expected exactly four corners in this perimeter"
}
set io_count 0
foreach io_side {top bottom left right} {
    set io_side_count [llength [dict get $io_rows $io_side]]
    incr io_count $io_side_count
    puts "$io_side : $io_side_count PAD"
}
if {$io_count == 0} {error "No CLASS PAD instances; check native LEF"}
set io_tmp_path ../my_soc_top/io_registration_tmp.io
set io_fd [open $io_tmp_path w]
puts $io_fd "(globals\n version = 3\n io_order = default\n)\n(iopad"
foreach io_side {topright top topleft left bottomleft bottom bottomright right} {
    puts $io_fd " ($io_side"
    if {[dict exists $io_corners $io_side]} {
        lassign [dict get $io_corners $io_side] io_name io_cell io_ori
        puts $io_fd [format {  (inst name="%s" cell="%s" orientation=%s place_status=fixed)} $io_name $io_cell $io_ori]
    } else {
        foreach io_row [lsort -real -index 0 [dict get $io_rows $io_side]] {
            lassign $io_row io_offset io_name io_cell io_indent io_ori
            puts $io_fd [format {  (inst name="%s" cell="%s" offset=%.6f indent=%.6f orientation=%s place_status=fixed)} $io_name $io_cell $io_offset $io_indent $io_ori]
        }
    }
    puts $io_fd " )"
}
puts $io_fd ")"
close $io_fd

loadIoFile $io_tmp_path -noAdjustDieSize -specifiedIosOnly
foreach io_name [dict keys $io_before] {
    set io_inst [dbGet top.insts.name $io_name -p]
    lassign [dict get $io_before $io_name] io_old_box io_old_ori
    set io_new_box [lindex [dbGet $io_inst.box] 0]
    foreach io_old_value $io_old_box io_new_value $io_new_box {
        if {abs($io_old_value-$io_new_value) > $io_tol} {
            error "IO moved during side registration: $io_name"
        }
    }
    if {[dbGet $io_inst.orient] ne $io_old_ori} {
        error "IO orientation changed during side registration: $io_name"
    }
}
file delete $io_tmp_path
saveIoFile -locations -includeCellName ../my_soc_top/my_soc_top_io_registered.io
defOut ../my_soc_top/my_soc_top_io_registered.def

dbGet top.fPlan.box
```

**本轮结果：** 步骤命令与对应自动检查已通过；详见`step_09.json`，独立验收范围以该JSON为准。

```json
{
  "step": 9,
  "commands_completed": true,
  "input_manifest_sha256": "702782c4bfff5f9afacfb9e9aa8060f390022b8b6792fff87aff1d7a6f6a087c",
  "automatic_checks": {},
  "scope": "Only the listed automatic checks are asserted. Tcl guards also check object counts, IO geometry and halo. Not complete signoff."
}
```

## 10 摆放键合焊盘

**做什么：** 为六个信号和28个供电/POC单元放34个Bond PAD。

**为什么：** IO PAD提供电路，Bond PAD提供封装金线接触的大金属，两者需要对齐。

**预期效果：** 34个键合焊盘与对应IO覆盖，这些预期覆盖区别于普通单元碰撞。

**关键参数：** Bond使用PAD60LU_OBV，沿边与对应IO一致；北/东边按实际尺寸和73.16 um深度计算，覆盖对应PAD是设计意图。

**本轮实际执行片段：** 下列是运行时保存的Tcl正文；宏路径已解析，其他变量结合配置与日志阅读。

`001_10_tcl.tcl`

```tcl
# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
addInst -physical -cell PAD60LU_OBV -inst i_bond_clk -loc {300.000000 3327.160000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_rst_n -loc {1400.000000 3327.160000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_tck -loc {250.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_tms -loc {450.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_tdi -loc {1400.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_tdo -loc {1600.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_N_vss_1 -loc {600.000000 3327.160000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_N_vss_2 -loc {700.000000 3327.160000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_N_vssio -loc {800.000000 3327.160000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_N_vdd_1 -loc {900.000000 3327.160000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_N_vdd_2 -loc {1000.000000 3327.160000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_N_vddio -loc {1100.000000 3327.160000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_N_poc -loc {1200.000000 3327.160000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_S_vss_1 -loc {600.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_S_vss_2 -loc {700.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_S_vssio -loc {800.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_S_vdd_1 -loc {900.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_S_vdd_2 -loc {1000.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_S_vddio -loc {1100.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_S_poc -loc {1200.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_W_vss_1 -loc {0.000000 600.000000} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_W_vss_2 -loc {0.000000 700.000000} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_W_vssio -loc {0.000000 800.000000} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_W_vdd_1 -loc {0.000000 900.000000} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_W_vdd_2 -loc {0.000000 1000.000000} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_W_vddio -loc {0.000000 1100.000000} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_W_poc -loc {0.000000 1200.000000} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_E_vss_1 -loc {3327.160000 600.000000} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_E_vss_2 -loc {3327.160000 700.000000} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_E_vssio -loc {3327.160000 800.000000} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_E_vdd_1 -loc {3327.160000 900.000000} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_E_vdd_2 -loc {3327.160000 1000.000000} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_E_vddio -loc {3327.160000 1100.000000} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_E_poc -loc {3327.160000 1200.000000} -ori R90 -place_status fixed -dontSnapToPlacementGrid
if {[llength [dbGet -e top.insts.cell.name PAD60LU_OBV -p2]] != 34} {error "Bond PAD count mismatch"}
```

**本轮结果：** 步骤命令与对应自动检查已通过；详见`step_10.json`，独立验收范围以该JSON为准。

```json
{
  "step": 10,
  "commands_completed": true,
  "input_manifest_sha256": "702782c4bfff5f9afacfb9e9aa8060f390022b8b6792fff87aff1d7a6f6a087c",
  "automatic_checks": {},
  "scope": "Only the listed automatic checks are asserted. Tcl guards also check object counts, IO geometry and halo. Not complete signoff."
}
```

## 11 绑定四个供电网络

**做什么：** 把核心PG引脚与VDD/VSS绑定，普通IO供电端绑定VDDPST/VSSPST。

**为什么：** 网络归属先正确，后面金属供电才能接对；Tie常量输出不能代替电源。

**预期效果：** 导出物理网表，逐个核对28个供电PAD、12普通端及四网独立。

**关键参数：** globalNetConnect是电气归属绑定，尚未画线。四网保持独立；N/S/W/E每侧vddio、poc接VDDPST，vssio接VSSPST。

**本轮实际执行片段：** 下列是运行时保存的Tcl正文；宏路径已解析，其他变量结合配置与日志阅读。

`001_11_tcl.tcl`

```tcl
# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
dbGet top.nets.name VDDPST
dbGet top.nets.name VSSPST

if {[dbGet top.nets.name VDDPST] eq "0x0"} {addNet VDDPST -power}
if {[dbGet top.nets.name VSSPST] eq "0x0"} {addNet VSSPST -ground}
globalNetConnect VDD -type pgpin -pin VDD -all -verbose
globalNetConnect VSS -type pgpin -pin VSS -all -verbose

attachTerm i_pad_N_vddio VDDPST VDDPST
attachTerm i_pad_N_poc VDDPST VDDPST
attachTerm i_pad_N_vssio VSSPST VSSPST
attachTerm i_pad_S_vddio VDDPST VDDPST
attachTerm i_pad_S_poc VDDPST VDDPST
attachTerm i_pad_S_vssio VSSPST VSSPST
attachTerm i_pad_W_vddio VDDPST VDDPST
attachTerm i_pad_W_poc VDDPST VDDPST
attachTerm i_pad_W_vssio VSSPST VSSPST
attachTerm i_pad_E_vddio VDDPST VDDPST
attachTerm i_pad_E_poc VDDPST VDDPST
attachTerm i_pad_E_vssio VSSPST VSSPST

saveNetlist ../my_soc_top/my_soc_top_pg_bound.v -phys
saveDesign ../my_soc_top/backup/my_soc_top_postPGConnect.enc
foreach sn {VDD VSS VDDPST VSSPST} {puts "SUPPLY $sn [dbGet top.nets.name $sn]"}
foreach side {N S W E} {foreach pair {{vddio VDDPST} {poc VDDPST} {vssio VSSPST}} {lassign $pair suffix pin; set it [dbGet top.insts.instTerms.name i_pad_${side}_${suffix}/$pin -p]; set nn [dbGet $it.net.name]; puts "SUPPLY_TERM i_pad_${side}_${suffix}/$pin $nn"; if {$nn ne $pin} {error "Wrong IO supply"}}}
```

**本轮结果：** 步骤命令与对应自动检查已通过；详见`step_11.json`，独立验收范围以该JSON为准。

```json
{
  "step": 11,
  "commands_completed": true,
  "input_manifest_sha256": "702782c4bfff5f9afacfb9e9aa8060f390022b8b6792fff87aff1d7a6f6a087c",
  "automatic_checks": {
    "four_supply_topology": {
      "program": "audit_io_topology.py",
      "exit_code": 0
    }
  },
  "scope": "Only the listed automatic checks are asserted. Tcl guards also check object counts, IO geometry and halo. Not complete signoff."
}
```

## 12 填充外围空隙

**做什么：** 在四边IO之间插入库规定的Filler并逐段检查。

**为什么：** 空隙可能使单元内部的外围供电轨中断，不能只看PAD数目正确。

**预期效果：** 四边从角块到角块连续、无意外间隙/重叠且朝向正确。

**关键参数：** 候选宽度20/10/5/1/0.5/0.005 μm由库决定，工具自动组合；四边使用独立前缀，便于定位和有范围返修。

**本轮实际执行片段：** 下列是运行时保存的Tcl正文；宏路径已解析，其他变量结合配置与日志阅读。

`001_12_tcl.tcl`

```tcl
# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
addIoFiller -cell {PFILLER20 PFILLER10 PFILLER5 PFILLER1 PFILLER05 PFILLER0005} -prefix IOF_TOP -side top -fillerOrient R180
addIoFiller -cell {PFILLER20 PFILLER10 PFILLER5 PFILLER1 PFILLER05 PFILLER0005} -prefix IOF_BOTTOM -side bottom -fillerOrient R0
addIoFiller -cell {PFILLER20 PFILLER10 PFILLER5 PFILLER1 PFILLER05 PFILLER0005} -prefix IOF_LEFT -side left -fillerOrient R270
addIoFiller -cell {PFILLER20 PFILLER10 PFILLER5 PFILLER1 PFILLER05 PFILLER0005} -prefix IOF_RIGHT -side right -fillerOrient R90

foreach prefix {IOF_TOP IOF_BOTTOM IOF_LEFT IOF_RIGHT} {puts "IO_FILLER $prefix [llength [dbGet -e top.insts.name ${prefix}*]]"}
defOut ../my_soc_top/my_soc_top_postIOFiller.def
```

`002_12_check_tcl.tcl`

```tcl
# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
set io_segments [dict create N {} S {} W {} E {}]
foreach ip [dbGet top.insts.cell.baseClass pad -p2] {
 lassign [lindex [dbGet $ip.box] 0] x0 y0 x1 y1
 if {abs($y1-3400.320000)<0.001} {set side N;set a $x0;set b $x1;set want R180} elseif {abs($y0)<0.001} {set side S;set a $x0;set b $x1;set want R0} elseif {abs($x0)<0.001} {set side W;set a $y0;set b $y1;set want R270} elseif {abs($x1-3400.320000)<0.001} {set side E;set a $y0;set b $y1;set want R90} else {error "PAD not on a Die edge"}
 if {[dbGet $ip.orient] ne $want} {error "Wrong IO orientation"}
 dict lappend io_segments $side [list $a $b [dbGet $ip.name]]
}
foreach side {N S W E} {
 set last 115.0
 foreach seg [lsort -real -index 0 [dict get $io_segments $side]] {lassign $seg a b nm;if {abs($a-$last)>0.001} {error "IO gap/overlap at $side $nm : $last to $a"};set last $b}
 set eda_edge_end [expr {$side in {N S} ? 3285.320000 : 3285.320000}]
 if {abs($last-$eda_edge_end)>0.001} {error "IO edge incomplete"}
 puts "IO_EDGE $side [llength [dict get $io_segments $side]] continuous 115-1685.4 correct_orientation"
}
saveDesign ../my_soc_top/backup/my_soc_top_postIOFiller.enc
```

**本轮结果：** 步骤命令与对应自动检查已通过；详见`step_12.json`，独立验收范围以该JSON为准。

```json
{
  "step": 12,
  "commands_completed": true,
  "input_manifest_sha256": "702782c4bfff5f9afacfb9e9aa8060f390022b8b6792fff87aff1d7a6f6a087c",
  "automatic_checks": {},
  "scope": "Only the listed automatic checks are asserted. Tcl guards also check object counts, IO geometry and halo. Not complete signoff."
}
```

## 13 固定主SRAM并留白

**做什么：** 按配置放置唯一主SRAM，增加Halo并核对实际四边留白。

**为什么：** 宏内部几何已固定，旁边要留接线空间；指定26不一定等于实际26。

**预期效果：** 实际留白每边至少20 um，宏和留白在规划允许区域内。

**关键参数：** macro_xy_um默认(250,650)；Halo参数26 um用于补偿本宏LEF边界差异，最终实际四边留白仍必须至少20 um。

**本轮实际执行片段：** 下列是运行时保存的Tcl正文；宏路径已解析，其他变量结合配置与日志阅读。

`001_13_tcl.tcl`

```tcl
# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
placeInstance i_mainmem/i_sram/i_macro 250.000000 650.000000 R0 -fixed
addHaloToBlock 26 26 26 26 i_mainmem/i_sram/i_macro -snapToSite
dbGet [dbGet top.insts.name i_mainmem/i_sram/i_macro -p].box
dbGet [dbGet top.insts.name i_mainmem/i_sram/i_macro -p].pHaloBox
checkFPlan -reportUtil -outFile ../my_soc_top/my_soc_top_floorplan_check.rpt

set mb [lindex [dbGet [dbGet top.insts.name i_mainmem/i_sram/i_macro -p].box] 0]
set hb [lindex [dbGet [dbGet top.insts.name i_mainmem/i_sram/i_macro -p].pHaloBox] 0]
lassign $mb mx0 my0 mx1 my1
lassign $hb hx0 hy0 hx1 hy1
set hm [list [expr {$mx0-$hx0}] [expr {$my0-$hy0}] [expr {$hx1-$mx1}] [expr {$hy1-$my1}]]
puts "ACTUAL_HALO_MARGINS $hm"
foreach m $hm {if {$m<20.0} {error "SRAM halo is less than 20 um"}}
saveDesign ../my_soc_top/backup/my_soc_top_postMacroPlace.enc
```

**本轮结果：** 步骤命令与对应自动检查已通过；详见`step_13.json`，独立验收范围以该JSON为准。

```json
{
  "step": 13,
  "commands_completed": true,
  "input_manifest_sha256": "702782c4bfff5f9afacfb9e9aa8060f390022b8b6792fff87aff1d7a6f6a087c",
  "automatic_checks": {},
  "scope": "Only the listed automatic checks are asserted. Tcl guards also check object counts, IO geometry and halo. Not complete signoff."
}
```

## 14 建立顶层物理端口

**做什么：** 为六个信号与四个电源接口创建明确的M4矩形。

**为什么：** 逻辑端口只表示接口名称，DEF/LEF/GDS还需要知道哪层金属、哪个位置。

**预期效果：** 十个端口的矩形、方向和用途与当前geometry计划一致。

**关键参数：** 十个M4矩形均10×1 um，位置跟随实际Die与PAD偏移；五INPUT、一OUTPUT、四INOUT，电源USE正确。

**本轮实际执行片段：** 下列是运行时保存的Tcl正文；宏路径已解析，其他变量结合配置与日志阅读。

`001_14_tcl.tcl`

```tcl
# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
createPhysicalPin clk_i -net clk_i -layer METAL4 -rect {310.000000 3397.920000 320.000000 3398.920000}
createPhysicalPin rst_ni -net rst_ni -layer METAL4 -rect {1410.000000 3397.920000 1420.000000 3398.920000}
createPhysicalPin tck_i -net tck_i -layer METAL4 -rect {260.000000 1.000000 270.000000 2.000000}
createPhysicalPin tms_i -net tms_i -layer METAL4 -rect {460.000000 1.000000 470.000000 2.000000}
createPhysicalPin td_i -net td_i -layer METAL4 -rect {1410.000000 1.000000 1420.000000 2.000000}
createPhysicalPin td_o -net td_o -layer METAL4 -rect {1610.000000 1.000000 1620.000000 2.000000}
createPGPin VDD -net VDD -geom METAL4 910.000000 3397.920000 920.000000 3398.920000
createPGPin VSS -net VSS -geom METAL4 610.000000 3397.920000 620.000000 3398.920000
createPGPin VDDPST -net VDDPST -geom METAL4 1110.000000 3397.920000 1120.000000 3398.920000
createPGPin VSSPST -net VSSPST -geom METAL4 810.000000 3397.920000 820.000000 3398.920000
defOut ../my_soc_top/my_soc_top_physicalPins.def
eda_picture 14_floorplan.gif
```

**本轮结果：** 步骤命令与对应自动检查已通过；详见`step_14.json`，独立验收范围以该JSON为准。

```json
{
  "step": 14,
  "commands_completed": true,
  "input_manifest_sha256": "702782c4bfff5f9afacfb9e9aa8060f390022b8b6792fff87aff1d7a6f6a087c",
  "automatic_checks": {
    "physical_pins": {
      "ports": [
        "VDD",
        "VDDPST",
        "VSS",
        "VSSPST",
        "clk_i",
        "rst_ni",
        "tck_i",
        "td_i",
        "td_o",
        "tms_i"
      ],
      "dbu_per_um": 2000,
      "all_rectangles_directions_uses_match_geometry_plan": true
    }
  },
  "scope": "Only the listed automatic checks are asserted. Tcl guards also check object counts, IO geometry and halo. Not complete signoff."
}
```

## 15 建立核心及SRAM电源环

**做什么：** 用M4/M5在核心和宏周围生成VDD/VSS环。

**为什么：** 供电需要较低阻抗的分配骨架，环提供后续条带和引脚接入目标。

**预期效果：** 环的特殊布线DRC通过；此时还不表示所有单元已有金属供电。

**关键参数：** 上下M5、左右M4；核心宽10/间距2/偏移5，宏环宽4/间距2/偏移10，单位μm。selected限定宏环只围绕目标SRAM。

**本轮结果：未完成。**

## 16 铺设基础供电条带

**做什么：** 生成M4纵向与M5横向VDD/VSS条带。

**为什么：** 只在边缘做环无法把电流送到内部，条带向核心深处分配供电。

**预期效果：** 建立基础网格，线宽/间距/节距采用明确的教学工艺配置。

**关键参数：** M4宽2、双网间距1、同组重复间距20；M5宽4、双网间距2、重复间距30。break_at限制在block/outer ring处断开，不直接穿越被阻挡的低层宏几何。

**本轮结果：未完成。**

## 17 连接SRAM原生电源引脚

**做什么：** 通过sroute把真实宏电源引脚接到宏环。

**为什么：** 绑定网络名不等于金属已接通；要尊重宏引脚层和内部阻挡。

**预期效果：** 宏PG引脚归属正确并生成接入金属，保留查询记录。

**关键参数：** connect blockPin限定宏针脚；inst只选本轮按宏型号查询出的唯一SRAM实例；M3/M4为针脚范围，M3–M5为引出跨层范围。

**本轮结果：未完成。**

## 18 使用高层跨越SRAM

**做什么：** 在宏区域上方增加M6供电条带。

**为什么：** 宏占用了部分低层资源，需要合法的高层连接帮助跨越。

**预期效果：** 按当前宏位置生成区域，使用VDD/VSS分别错开的高层供电。

**关键参数：** M6区域根据宏当前位置与固定宏尺寸生成；VDD/VSS错开，不能把高层跨越误当作穿越宏内部低层阻挡。

**本轮结果：未完成。**

## 19 补充宏附近横向供电

**做什么：** 在宏区域生成M5横向条带并检查特殊布线。

**为什么：** 不同层之间需要过孔和合适接入，不能只看二维图有交叉就认为连通。

**预期效果：** 补充网格并导出阶段DEF，特殊布线DRC通过。

**关键参数：** M5区域随宏位置移动；线宽4、间距2、组距30 um为当前教学工艺配置，最终看特殊布线DRC与连通。

**本轮结果：未完成。**

## 20 连接核心供电PAD与环

**做什么：** 从16个核心供电PAD引脚接到核心电源环。

**为什么：** 外部供电必须经过实际PAD金属进入环，不能只在网表中同名。

**预期效果：** 形成外围到核心环的金属连接，保留阶段连通/DRC报告。

**关键参数：** PAD接入区域使用实际宽/高减边缘余量，padPinSplit、M2到M5过孔范围遵循当前库，不把旧1720坐标写死。

**本轮结果：未完成。**

## 21 建立标准单元行电源轨

**做什么：** 用M1沿单元行布置VDD/VSS轨并接到网格。

**为什么：** 每行标准单元都需要就近电源，只有高层环和条带仍不能直接供电。

**预期效果：** 保留完整PG及排除悬线检查的阶段报告；最终步骤33仍要求完整PG清零。

**关键参数：** 行轨在M1，向M4连接；这里连通检查的noAntenna排除悬线检查，与步骤31的工艺天线检查不是同一件事。完整PG报告保留且最终重新验收。

**本轮结果：未完成。**

## 22 核对IO原生供电轨

**做什么：** 检查IO侧连通报告，并读取真实库GDS核对长轨截面和角部转接。

**为什么：** 本库LEF没有完整呈现部分原生轨，需要用真实几何与步骤12连续位置共同判断。

**预期效果：** 仅对经验证的VDDPST/VSSPST两项抽象限制分类记录，不放过其他开短路。

**关键参数：** 先核对步骤12四边连续/朝向；解析原生IO GDS的M4长轨和Corner转角。该检查只覆盖所述轨几何，不代替全芯片独立LVS。

**本轮结果：未完成。**

## 23 插入Tap和去耦电容

**做什么：** 按库规则插阱连接单元及Decap，绑定PG并复查。

**为什么：** 器件的硅体区域需要参考电压；去耦电容帮助缓和短时供电波动。

**预期效果：** Tap覆盖规则和特殊布线DRC通过；这不代替供电压降分析。

**关键参数：** Tap cellInterval60、checkerBoard；verifyWellTap rule30对应该教学目标，不是独立核实的foundry签核规则。site吸附后间距59.920；Decap skipRow1隔行插入。

**本轮结果：未完成。**

## 24 放置标准单元

**做什么：** 运行place_opt_design，按连接与时序安排大量普通逻辑。

**为什么：** 既要放得下，又要给布线留空间并减少长距离连接。

**预期效果：** 没有未放置或非法普通单元；仅保留明确的34组IO/Bond覆盖。

**关键参数：** preroute_as_obs={}避免将高层PG投影成整条禁放带；显式ignore_scan=true/reorder_scan=false。ignoreOutOfCore限定此标准单元检查范围，不豁免核心违规。

**本轮结果：未完成。**

## 25 给常量输入插Tie

**做什么：** 先为PAD控制脚插常量单元，再插核心常量并排除12个普通供电端。

**为什么：** 常量驱动给逻辑输入提供0/1，不能误接到IO电源网络。

**预期效果：** 细查六个PAD控制值、四网独立、供电端未被Tie取代。

**关键参数：** 先写12端排除表；keepExisting保持第一轮IO Tie；刷新PG、refinePlace，导出postTie.v。最终是否满足电容仍以RC报告为准。

**本轮结果：未完成。**

## 26 检查时钟树之前的时序

**做什么：** 分别计算preCTS Setup和Hold并检查核心PG。

**为什么：** 时钟树尚未真实建立，先定位估计线长和理想时钟假设下的问题。

**预期效果：** 保存两类报告；早期残项被记录，最终是否达标在布线后重新判断。

**关键参数：** expandedViews展开活动视图结果；WNS/TNS、违规数量与Real/Total DRV要分开读。preCTS仍未包含最终时钟树和真实全部信号RC。

**本轮结果：未完成。**

## 27 定义时钟树与源模型

**做什么：** 为sys_clk和jtag_clk准备时钟树，设置源转换时间、电容能力和时间预算。

**为什么：** 同一时钟要驱动很多寄存器；外部源也有有限驱动能力。

**预期效果：** 两路真实树有完整规格，虚拟JTAG参考不创建物理树。

**关键参数：** 仅sys_clk/jtag_clk是真实树；0.5 ns输入转换、5 pF源允许负载、0.47/0.2 ns Setup/Hold不确定度沿用已说明的首轮模型，不代表物理添加对应电容或延时。

**本轮结果：未完成。**

## 28 构建并分析真实时钟树

**做什么：** 运行CCOpt，将真实时钟网络延时纳入Setup/Hold分析。

**为什么：** 时钟到各处不再完全同时；偏差可能帮助Setup却恶化Hold。

**预期效果：** 保存树后检查点，放置合法，输出两类时序/电气报告。

**关键参数：** set_propagated_clock只作用于sys_clk/jtag_clk；timing_io_use_clock_network_latency always按讲义使用网络延迟。虚拟参考不传播。

**本轮结果：未完成。**

## 29 按当前报告处理树后Hold

**做什么：** 只有当前报告需要时才做Hold优化，然后独立重查。

**为什么：** 新数据来得太早会破坏采样，可以加适当延时，同时保护Setup。

**预期效果：** 保存实际修复后结果；pre-route估计残项不会被写成最终通过。

**关键参数：** 只按当前Hold报告决定是否运行修复，保护Setup；布线前估计残项明确记录，不假称最终满足。

**本轮结果：未完成。**

## 30 正式布线

**做什么：** 按允许金属层执行时序驱动布线，连接真实信号网络。

**为什么：** 前面的连接估计还不是完整可制造的金属，正式布线会改变延时。

**预期效果：** 生成正式导线和过孔，随后必须检查几何、连通、天线及真实RC。

**关键参数：** clock nets first优先时钟路由；postRoute low、tQuantusForPostRoute=false使用现有CapTable，不调用缺少Quantus techfile的medium设置；SI保持关闭。

**本轮结果：未完成。**

## 31 检查并修工艺天线

**做什么：** 独立检查，再从本轮天线报告提取实际违规网，有限次修复。

**为什么：** 制造期间金属积累电荷可能损伤薄绝缘结构，不能复用旧违规网名。

**预期效果：** 天线、default DRC和常规信号连通通过，保留原始和修复报告。

**关键参数：** 从当前独立报告提取违规网络，最多max_repair_iterations次，默认3次；不使用历史网名。两项IO抽象限制只有同源步骤22证据齐备才可分类。

**本轮结果：未完成。**

## 32 真实RC下修复时序

**做什么：** 提取布线寄生，先按需要优化Setup，再处理Hold并独立重查。

**为什么：** 导线电阻电容会影响到达时间；布线前通过不等于布线后通过。

**预期效果：** 两种时序违规与Real/Total电气DRV归零，否则停止，不自动放宽时钟。

**关键参数：** 按当前Setup和Hold/DRV情况运行优化，hold_target_ns默认0.02 ns。目标不修改原SDC；达到上限仍不清零就停止。

**本轮结果：未完成。**

## 33 核心填充及最终复核

**做什么：** 插核心Filler后重新提取RC，检查放置、完整核心PG、几何、天线和时序。

**为什么：** 填充后设计发生变化，要在最终状态验收；中途排除悬线的PG检查不够。

**预期效果：** 最终各检查通过，保存可恢复的完整阶段点。

**关键参数：** ecoMode/fitGap按讲义匹配剩余空隙；check_signal_drc=true且add_fillers_with_drc=false，不允许为了填满而引入已知DRC。

**本轮结果：未完成。**

## 34 导出并交叉核对

**做什么：** 导出DEF、两种网表、SDC、SPEF/SDF、LEF、合并GDS。

**为什么：** 后续工具需要连接、位置、时间和真实几何的不同表达，它们必须一致。

**预期效果：** 核对十端口、尺寸、网表/SDF路径、寄生记录和GDS引用；不冒称独立工艺签核。

**关键参数：** GDS合并四套原生库输入，使用当前层映射和2000 DBU/um；SPEF/SDF取func_tt_io。检查尺寸与当前geometry.json一致，不硬编码旧实例数或GDS结构数。

**本轮结果：未完成。**
