# Reports/exports can be regenerated from the mapped write_design checkpoint.
file mkdir [file join $output_root reports]
file mkdir [file join $output_root outputs]
file mkdir [file join $output_root backup]
write_hdl -language v2001 > outputs/my_soc_top_postsyn.v
write_sdf -timescale ps -view func_tt > outputs/my_soc_top_tt.sdf
write_sdc -view func_tt > outputs/my_soc_top.sdc
check_design -all > reports/check_final.rpt
check_timing_intent -verbose -view func_tt > reports/timing_intent_final.rpt
report_area -detail > reports/area.rpt
report_gates > reports/gates.rpt
report_dp > reports/datapath.rpt
report_qor > reports/qor.rpt
report_clocks > reports/clocks.rpt
report_units > reports/units.rpt
report_design_rules > reports/design_rules.rpt
report_timing -max_paths 20 -view func_tt > reports/setup.rpt
report_timing -unconstrained -max_paths 20 -view func_tt > reports/unconstrained.rpt
set cdc_nets [get_nets -hierarchical async*]
set cdc_names [get_object_name $cdc_nets]
set cdc_file [open reports/cdc_nets.rpt w]
puts $cdc_file "CDC_NET_COUNT [llength $cdc_names]"
puts $cdc_file [join $cdc_names "\n"]
close $cdc_file
if {[llength $cdc_names] == 0} {error "CDC max-delay constraint matches no surviving nets"}
report_timing -through $cdc_nets -max_paths 20 -view func_tt > reports/cdc_timing.rpt
report_memory_cells > reports/memory_cells.rpt
report_sequential -hier > reports/sequential.rpt
report_clock_gating > reports/clock_gating.rpt
report_power -unit uW -by_hierarchy -view func_tt > reports/power_estimate.rpt
write_design -base_name backup/my_soc_top my_soc_top
report_messages -all > reports/messages_final.rpt
puts "ASIC_SYNTHESIS_FINISHED"
