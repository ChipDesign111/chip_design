# Complete project-owned SoC. Do not substitute the CPU-only course netlist.
source run_config.tcl
file mkdir [file join $output_root reports]
file mkdir [file join $output_root outputs]
file mkdir [file join $output_root backup]
set_db information_level 6
set_db design_process_node 180
set_db max_cpus_per_server $cpu_count
set_db auto_super_thread true
set_db init_hdl_search_path [list [file join $design_root rtl/include] [file join $design_root rtl]]
set_db hdl_max_loop_limit 65536
set_db hdl_track_filename_row_col true
set_db hdl_parameterize_module_name false
set_db hdl_keep_first_module_definition true
set_db syn_generic_effort medium
set_db syn_map_effort medium
set_db syn_opt_effort medium
set_db lp_insert_clock_gating true
set_db lp_clock_gating_infer_enable true
set_db lp_power_unit uW
set_db lp_default_probability 0.5
set_db lp_default_toggle_rate 0.2
set_db tns_opto true
# Leave undriven nets detectable rather than silently assigning zeros.
read_mmmc [file join $script_root mmmc.tcl]
# Genus 19.17 needs a loaded target-library domain before LEF unit setup.
# Reading LEF first produces LBR-163 and inconsistent-unit diagnostics.
set_db lef_library $lef_files
read_hdl -language sv -f [file join $output_root rtl.f]
elaborate my_soc_top
init_design -top my_soc_top
uniquify [get_design my_soc_top] -verbose
set_db [vfind . -module *] .boundary_opto false
set_db [vfind . -design *] .retime false
check_design -all > reports/check_elaborated.rpt
check_timing_intent -verbose -view func_tt > reports/timing_intent_elaborated.rpt
report_messages > reports/messages_elaborated.rpt
syn_generic my_soc_top
check_design -all > reports/check_generic.rpt
syn_map my_soc_top
check_design -all > reports/check_mapped.rpt
syn_opt my_soc_top -incremental
write_design -base_name backup/my_soc_top my_soc_top
source [file join $script_root reports.tcl]
exit
