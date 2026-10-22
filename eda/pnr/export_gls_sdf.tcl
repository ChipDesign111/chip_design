# Standalone paired export from a completed checkpoint into fresh evidence.
# Never write the original physical output directory or its frozen STA SDF.
set script_root [file dirname [file normalize [info script]]]
foreach name {CHIP_GLS_CHECKPOINT CHIP_GLS_EVIDENCE} {
    if {![info exists ::env($name)]} {error "Missing required $name"}
}
set checkpoint [file normalize $::env(CHIP_GLS_CHECKPOINT)]
set evidence [file normalize $::env(CHIP_GLS_EVIDENCE)]
set gls_sdf [file join $evidence filtered.sdf.gz]
if {![file isdirectory $checkpoint]} {error "Missing completed checkpoint: $checkpoint"}
if {$evidence eq $checkpoint || [string first ${checkpoint}/ $evidence]==0} {
    error "Evidence must not be written inside the checkpoint: $evidence"
}
foreach name {actual_material_inputs.txt restored.sdc restored_path_adjust.tcl after_filter.sdc after_filter_path_adjust.tcl clock_trees.rpt skew_groups.rpt restored_setup restored_hold setup_paths.rpt hold_paths.rpt restored_raw_1.sdf.gz restored_raw_2.sdf.gz filtered.sdf.gz restored_raw_after.sdf.gz after_filter_setup after_filter_hold} {
    if {[file exists [file join $evidence $name]]} {
        error "Refusing to overwrite standalone export evidence: [file join $evidence $name]"
    }
}
regsub {\.dat$} $checkpoint {} context_base
set context ${context_base}.context.tcl
if {![file readable $context]} {error "Missing checkpoint context: $context"}
# config.tcl writes an input inventory. Isolate that and all report helpers in
# the new evidence directory even if CHIP_PNR_OUTPUT names frozen PNR outputs.
set prior_output_exists [info exists ::env(CHIP_PNR_OUTPUT)]
if {$prior_output_exists} {set prior_output $::env(CHIP_PNR_OUTPUT)}
set ::env(CHIP_PNR_OUTPUT) $evidence
set config_failed [catch {source [file join $script_root config.tcl]} config_answer config_options]
if {$prior_output_exists} {
    set ::env(CHIP_PNR_OUTPUT) $prior_output
} else {
    unset ::env(CHIP_PNR_OUTPUT)
}
if {$config_failed} {return -options $config_options $config_answer}
proc gls_sdc_commands {path} {
    set handle [open $path r]
    set commands {}
    foreach line [split [read $handle] \n] {
        set line [string trim $line]
        if {$line ne {} && [string index $line 0] ne {#}} {lappend commands $line}
    }
    close $handle
    return [join $commands \n]
}
setLibraryUnit -cap 1pf -time 1ns
restoreDesign $checkpoint my_soc_top
source $context
source [file join $script_root geometry_helpers.tcl]
source [file join $script_root settings.tcl]
pnr4::assert_clock_periods
foreach name {sys_clk jtag_clk} {
    pnr4::assert {[get_property [get_clocks $name] is_propagated_clock]} "Expected propagated $name"
}
pnr4::assert {![get_property [get_clocks virtual_jtag_tck] is_propagated_clock]} "Expected ideal virtual reference"
pnr4::assert_io_supplies
file mkdir $evidence
write_sdc -view func_tt_io [file join $evidence restored.sdc]
write_sdc -path_adjust_only > [file join $evidence restored_path_adjust.tcl]
if {[file size [file join $evidence restored_path_adjust.tcl]]!=0} {error "Unexpected path adjustments"}
report_ccopt_clock_trees -clock_trees $pnr4::physical_trees -views {func_tt_io} -file [file join $evidence clock_trees.rpt]
report_ccopt_skew_groups -views {func_tt_io} -include_reporting_only_skew_groups -file [file join $evidence skew_groups.rpt]
timeDesign -postRoute -expandedViews -outDir [file join $evidence restored_setup]
timeDesign -postRoute -hold -expandedViews -outDir [file join $evidence restored_hold]
report_timing -late -max_paths 50 > [file join $evidence setup_paths.rpt]
report_timing -early -max_paths 50 > [file join $evidence hold_paths.rpt]
# Same-session controls distinguish restore/recompute rounding from clipping.
# Never use target_application verilog: its preset changes parallel-arc values.
set sdf_sta_options {-min_view func_tt_io -typ_view func_tt_io -max_view func_tt_io -target_application sta -edges check_edge -collapse_internal_pins -setuphold merge_when_paired -recrem merge_when_paired -min_period_edges none -recompute_delay_calc}
write_sdf {*}$sdf_sta_options [file join $evidence restored_raw_1.sdf.gz]
write_sdf {*}$sdf_sta_options [file join $evidence restored_raw_2.sdf.gz]
write_sdf {*}$sdf_sta_options -filter $gls_sdf
write_sdf {*}$sdf_sta_options [file join $evidence restored_raw_after.sdf.gz]
pnr4::assert_clock_periods
foreach name {sys_clk jtag_clk} {
    pnr4::assert {[get_property [get_clocks $name] is_propagated_clock]} "Expected propagated $name after SDF export"
}
pnr4::assert {![get_property [get_clocks virtual_jtag_tck] is_propagated_clock]} "Expected ideal virtual reference after SDF export"
pnr4::assert_io_supplies
write_sdc -view func_tt_io [file join $evidence after_filter.sdc]
write_sdc -path_adjust_only > [file join $evidence after_filter_path_adjust.tcl]
if {[file size [file join $evidence after_filter_path_adjust.tcl]]!=0} {error "Unexpected path adjustments after SDF export"}
if {[gls_sdc_commands [file join $evidence restored.sdc]] ne [gls_sdc_commands [file join $evidence after_filter.sdc]]} {
    error "SDF export changed restored SDC commands"
}
timeDesign -postRoute -expandedViews -outDir [file join $evidence after_filter_setup]
timeDesign -postRoute -hold -expandedViews -outDir [file join $evidence after_filter_hold]
puts "PNR_GLS_SDF_EXPORT_COMPLETE $gls_sdf; audit RAW1/RAW2/filter/RAW_after before simulation"
exit 0
