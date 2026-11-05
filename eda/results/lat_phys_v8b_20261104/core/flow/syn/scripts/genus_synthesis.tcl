#####################################################################################
# Description:  Genus Logic Synthesis Main Script
# Modifier:     Mingxuan Li <mingxuanli_siris@163.com> [Peking University]
# Acknowledge:  Columbia University, System Level Design Group
#####################################################################################

# -----------------------------------------------------------------------------------
# Design Initialization
# -----------------------------------------------------------------------------------

# set main variables: technology, project, logic synthesis, etc.
# set main configurations, load libraries, and read hdl
source ../../config/user_define.tcl
source ../../config/global_define.tcl
switch $syn_opt_level {
"standard"  {source ../scripts/init_syn_standard_opt.tcl}
default {error "Only syn_opt_level standard is supported by this flow"}
}

# uniquify the instances under the specified design or subdesign
uniquify [get_design $rm_core_top ] -verbose

# preserve module

# timing contraints applied only to synthesis
set_interactive_constraint_modes func

# set dont use cell
report_runtime start

# -----------------------------------------------------------------------------------
# Design and Constraint Check
# -----------------------------------------------------------------------------------
# check design constraints
foreach view $proj(analysis_view,setup) {
check_timing_intent -verbose -view $view > $log_syn(reports_path)/time_intent/${view}_timing_intent_elab.rpt
}

# check design structure, including undriven ports, any cells not in .lib/.lef, etc.
check_design -all > $log_syn(reports_path)/runtime/check_elab.rpt
report_runtime check_design

# -----------------------------------------------------------------------------------
# Logic Synthesis and PPA Optimization
# -----------------------------------------------------------------------------------
# creating cost groups
foreach view $proj(analysis_view,setup) {
  define_cost_group -name C2C_$view -design $log_syn(design)
  define_cost_group -name I2C_$view -design $log_syn(design)
  define_cost_group -name C2O_$view -design $log_syn(design)
  define_cost_group -name I2O_$view -design $log_syn(design)
}

# assign paths that meet criteria to a cost group
foreach view $proj(analysis_view,setup) {
  path_group -from  [all_registers] -to [all_registers] -view $view -group C2C_$view -name C2C_path_$view
  path_group -from  [all_inputs]    -to [all_registers] -view $view -group I2C_$view -name I2C_path_$view
  path_group -from  [all_registers] -to [all_outputs]   -view $view -group C2O_$view -name C2O_path_$view
  path_group -from  [all_inputs]    -to [all_outputs]   -view $view -group I2O_$view -name I2O_path_$view
}

# Use the explicit SDC target; no hidden path_adjust tightening.


# starting synthesis into generic gates
syn_generic $log_syn(design)
check_design -all > $log_syn(reports_path)/runtime/check_syn_generic.rpt
report_messages > $log_syn(reports_path)/runtime/syn_generic_message.rpt
report_runtime syn_generic

# map a design from generic gates to a technology library
syn_map $log_syn(design)
check_design -all > $log_syn(reports_path)/runtime/check_map.rpt
report_messages > $log_syn(reports_path)/runtime/syn_map_message.rpt
report_runtime syn_map

# incrementally optimize PPA
if {$syn_opt_level ne "none"} {
syn_opt $log_syn(design) -incremental
check_design -all > $log_syn(reports_path)/runtime/check_opt.rpt
report_messages > $log_syn(reports_path)/runtime/syn_opt_message.rpt
report_runtime syn_opt
}

# -----------------------------------------------------------------------------------
# Final Report
# -----------------------------------------------------------------------------------
# create qualification reports
report_area -detail     > $log_syn(reports_path)/area/area.rpt
report_boundary_opt     > $log_syn(reports_path)/others/boundary_opto.rpt
report_clocks           > $log_syn(reports_path)/others/clocks.rpt
report_design_rules     > $log_syn(reports_path)/others/design_rules.rpt
report_dp               > $log_syn(reports_path)/others/datapath.rpt
report_clock_gating     > $log_syn(reports_path)/others/clock_gating.rpt
report_loop             > $log_syn(reports_path)/others/loop_breakers.rpt
report_qor              > $log_syn(reports_path)/others/qor.rpt
report_yield            > $log_syn(reports_path)/others/des_yield.rpt
report_gates            > $log_syn(reports_path)/others/gates.rpt
report_ple              > $log_syn(reports_path)/others/ple.rpt
report_units            > $log_syn(reports_path)/others/des_units.rpt
report_sequential -hier > $log_syn(reports_path)/others/des_registers.rpt
report_memory_cells     > $log_syn(reports_path)/others/des_memories.rpt

foreach view $proj(analysis_view,setup) {
  report_timing -max_paths 10           -view $view > $log_syn(reports_path)/timing/${view}_timing.rpt
  report_power  -unit uW                -view $view > $log_syn(reports_path)/power/${view}_power.rpt
  report_power  -unit uW -by_hierarchy  -view $view > $log_syn(reports_path)/power/${view}_power_hier.rpt
}

# generate Standard Delay Format @ tt_1p80v_25c
write_sdf -timescale ps -view func_tt_1p80v_25c > $log_syn(outputs_path)/$log_syn(design)_tt_1p80v_25c.sdf

# write netlist
write_hdl -language v2001 > $log_syn(outputs_path)/$log_syn(design)_postsyn.v

# store design for recovery
write_design -base_name $log_syn(outputs_path)/backup/$log_syn(design) $log_syn(design)

report_messages -all
report_runtime finish

puts "
======================
= SYNTHESIS FINISHED =
=                    =
=      ^     ^       =
=        \\_/         =
=                    =
=  Congratulations!  =
======================"

puts "EDA_SYNTHESIS_COMMANDS_COMPLETE"
