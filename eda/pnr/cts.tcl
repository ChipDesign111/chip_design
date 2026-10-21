# Full CCOpt and post-CTS hold repair. main.tcl owns timestamped checkpoints.
pnr4::assert {[llength [info procs pnr4::placed_checks]]==1} "Restore the placement-stage Tcl context first"
setMultiCpuUsage -localCpu $pnr_cpus
pnr4::assert_clock_periods
pnr4::assert_io_supplies

# Preserve the synthesis baseline. This changes no input SDC file and applies
# no path adjustments. The virtual clock retains its imported uncertainty.
set_interactive_constraint_modes [all_constraint_modes -active]
set_clock_uncertainty -setup 0.52 [get_clocks {sys_clk jtag_clk}]
set_clock_uncertainty -hold 0.2 [get_clocks {sys_clk jtag_clk}]
set_input_transition 0.5 [get_ports {clk_i tck_i}]
set_interactive_constraint_modes {}
set_ccopt_property primary_delay_corner delay_tt_io
set_ccopt_property update_io_latency false
set_ccopt_property force_update_io_latency false

pnr4::assert {[llength [get_ccopt_clock_trees *]]==0} "Clock trees already exist; restart CTS from the placement checkpoint"
set specification [file join $output_root outputs ccopt_clock_tree_spec.tcl]
# -file writes the extracted specification without executing it, so source it
# exactly once. Keep it as evidence of the two physical clock sources.
create_ccopt_clock_tree_spec -views {func_tt_io} -file $specification
source $specification
set physical_trees [lsort [get_ccopt_clock_trees *]]
pnr4::assert {$physical_trees eq [lsort {sys_clk jtag_clk}]} "Unexpected physical clock trees: $physical_trees"
set pnr4::physical_trees $physical_trees
foreach clock_tree $physical_trees {
    set_ccopt_property source_output_max_trans 0.5 -clock_tree $clock_tree
    set_ccopt_property source_max_capacitance 5.0 -clock_tree $clock_tree
}
set handle [open [file join $output_root reports cts_source_model.rpt] w]
puts $handle "system_period_ns 20.0"
puts $handle "jtag_period_ns 100.0"
puts $handle "physical_trees $physical_trees"
puts $handle "setup_uncertainty_ns 0.52"
puts $handle "hold_uncertainty_ns 0.2"
puts $handle "source_transition_ns 0.5"
puts $handle "source_max_capacitance_pf 5.0"
puts $handle "virtual_jtag_tck is a reference clock, not a physical clock tree"
close $handle

set prerequisites [file join $output_root reports ccopt_prerequisites.rpt]
redirect $prerequisites {ccopt_design -check_prerequisites} -tee
set handle [open $prerequisites r]
set prerequisite_text [read $handle]
close $handle
if {[regexp -nocase -line {^[ \t]*(\*\*)?(ERROR|FATAL)[ :]} $prerequisite_text]} {
    error "CCOpt prerequisite diagnostics contain an error; inspect $prerequisites"
}
report_ccopt_clock_trees -clock_trees $physical_trees -views {func_tt_io} -file [file join $output_root reports prects_clock_trees.rpt]
ccopt_design -expandedViews -outDir [file join $output_root reports ccopt]
pnr4::assert {[dbGet top.statusClockSynthesized]} "CCOpt did not mark the clock network synthesized"

# Propagate exactly the two physical clocks, never the virtual IO reference.
set_interactive_constraint_modes [all_constraint_modes -active]
set_global timing_io_use_clock_network_latency always
set_propagated_clock [get_clocks {sys_clk jtag_clk}]
set_interactive_constraint_modes {}
foreach clock {sys_clk jtag_clk} {
    pnr4::assert {[get_property [get_clocks $clock] is_propagated_clock]} "Clock is still ideal after CTS: $clock"
}
pnr4::assert {![get_property [get_clocks virtual_jtag_tck] is_propagated_clock]} "Virtual IO reference unexpectedly became propagated"
pnr4::assert_clock_periods
globalNetConnect VDD -type pgpin -pin VDD -all
globalNetConnect VSS -type pgpin -pin VSS -all
pnr4::placed_checks postcts_raw
timeDesign -postCTS -expandedViews -outDir [file join $output_root reports postCTS_raw]
timeDesign -postCTS -hold -expandedViews -outDir [file join $output_root reports postCTS_raw]
report_ccopt_clock_trees -clock_trees $physical_trees -views {func_tt_io} -file [file join $output_root reports postcts_raw_clock_trees.rpt]
report_ccopt_skew_groups -views {func_tt_io} -include_reporting_only_skew_groups -file [file join $output_root reports postcts_raw_skew_groups.rpt]

# Repair hold without permitting setup TNS degradation. A zero target leaves
# the specified 0.2 ns uncertainty intact; no timing exception is loosened.
setOptMode -fixHoldAllowSetupTnsDegrade false -holdTargetSlack 0
optDesign -postCTS -hold -expandedViews -outDir [file join $output_root reports postCTS_holdFix]
globalNetConnect VDD -type pgpin -pin VDD -all
globalNetConnect VSS -type pgpin -pin VSS -all
pnr4::placed_checks postcts_hold_fixed
verify_drc -check_only special -report [file join $output_root reports postcts_special_drc.rpt]
pnr4::assert_clock_periods
timeDesign -postCTS -expandedViews -outDir [file join $output_root reports postCTS_final]
timeDesign -postCTS -hold -expandedViews -outDir [file join $output_root reports postCTS_final]
report_ccopt_clock_trees -clock_trees $physical_trees -views {func_tt_io} -file [file join $output_root reports postcts_clock_trees.rpt]
report_ccopt_skew_groups -views {func_tt_io} -include_reporting_only_skew_groups -file [file join $output_root reports postcts_skew_groups.rpt]
report_ccopt_clock_tree_structure -clock_trees $physical_trees -show_sinks -file [file join $output_root reports postcts_clock_structure.rpt]
report_clocks > [file join $output_root reports postcts_clocks.rpt]
write_sdc -view func_tt_io [file join $output_root outputs my_soc_top_postcts.sdc]
puts "PNR_CTS_FINISHED; inspect clock-tree/skew, setup/hold, placement and core-PG reports"
