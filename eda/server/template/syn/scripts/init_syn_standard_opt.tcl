#####################################################################################
# Description:  Genus Logic Synthesis Configuration with Standard Optimization
# Modifier:     Mingxuan Li <mingxuanli_siris@163.com> [Peking University]
# Acknowledge:  Columbia University, System Level Design Group
#####################################################################################

# -----------------------------------------------------------------------------------
# Basic RTL Elabration & Synthesis Optimization
# -----------------------------------------------------------------------------------
set log_syn(design)                 ${rm_core_top}
set log_syn(sdc_syn_path)           ../scripts
set log_syn(outputs_path)           ../${rm_core_top}
set log_syn(reports_path)           ../${rm_core_top}/reports
set log_syn(hdl_search_path)        {../../src/SoC_cv32e40p/soc/rtl/include}
set log_syn(sv_list)                ../../src/filelist_syn.f

# specify [0, 11], the higher the value, the more verbose the output
set_db information_level 6

# specify the process technology in nanometers
set_db design_process_node $tech(process_node)

# specify maximum number of available CPUs
set_db max_cpus_per_server $syn_cpus
set_db auto_super_thread true

# specify search path for "`include" in HDL
set_db init_hdl_search_path $log_syn(hdl_search_path)

# connect any undriven signal to zero
set_db hdl_unconnected_value 0

# determine the maximum number of iterations for unfolding in a loop construct
set_db hdl_max_loop_limit 65536

# track file, row, column information
set_db hdl_track_filename_row_col true

# remove unused filp-flops, latches and registers
# only affect "elaborate" command
set_db hdl_preserve_unused_flop         false
set_db hdl_preserve_unused_latch        false
set_db hdl_preserve_unused_registers    false

# do not add parameter value to module name for top-level design
set_db hdl_parameterize_module_name false

# retain first seen definition for a given module name
set_db hdl_keep_first_module_definition true

# specify the format of the suffix added to the original module name
set_db hdl_parameter_naming_style ""

# technology libraries and LEF libraries
set_db init_lib_search_path $tech(pdk_lib_path)

# specify LEF libraries for technology mapping
# cells in .lib but not in .lef will be marked as avoid
# cell area defined in LEF will be used instead of .lib
# LEF loading moved after read_mmmc to avoid Genus 19.17 LBR-163.

# default probability of a net being high
# only apply to nets at top level
set_db lp_default_probability 0.5

# default toggle rate
# only apply to nets at top level
set_db lp_default_toggle_rate 0.2
# insert clock-gating logic
set_db lp_insert_clock_gating true

# invoke advanced algorithm to identify additional clock-gating opportunities
set_db lp_clock_gating_infer_enable true

# case sensitive, to get more precise result, use a smaller unit
set_db lp_power_unit uW

# allow constant propagation through sequential instance
# thus allow removal of the instance
set_db optimize_constant_0_flops                    true
set_db optimize_constant_1_flops                    true
set_db optimize_constant_latches                    true
set_db optimize_constant_feedback_seqs              true

# allow merging with other equivalent
set_db optimize_merge_flops                         true
set_db optimize_merge_latches                       true

# remove flip-flops/instances if none of the outputs are connected
# only affect "syn_generic"/"syn_map" commands
set_db delete_unloaded_insts    false
set_db delete_unloaded_seqs     true

# optimization of case, if-else, etc.
# possible value: basic | advanced | none
set_db control_logic_optimization advanced

# the level of optimization of datapath logic area
# possible value: extreme / off / standard
# extreme may degrade timing
set_db dp_analytical_opt standard

# propagate switching activities
# possible value: high / low / medium
set_db iopt_lp_power_analysis_effort medium

# consider all the endpoints for negative slack optimization
set_db tns_opto true

# global effort to use for all synthesis commands
# by default (set to none), values of syn_generic_effort, syn_map_effort, syn_opt_effort are used
# otherwise value of this attribute overrides the individual settings of syn_generic_effort, syn_map_effort, syn_opt_effort
# possible value: none | low | medium | high | express
# default: none
set_db syn_global_effort medium

# optimization effort for "syn_generic" command
# possible value: medium / low / high / express / none
# default: medium
set_db syn_generic_effort medium

# optimization effort for "syn_map" command
# possible value: medium / low / high / express / none
set_db syn_map_effort medium

# optimization effort for "syn_opt" command
# possible value: medium / low / high / express / none /extreme
set_db syn_opt_effort medium

# default effort ensures verifiability
# use high effort casuses trade-off bwtween QoR and ease of formal verification
# possible value: medium | low | high
# default: medium
set_db retime_effort_level medium

# whether to write intermediate files to the verification directory
set_db write_verification_files false


# -----------------------------------------------------------------------------------
# read & elaborate RTL, construct database
# -----------------------------------------------------------------------------------
# read multi-mode multi-corner file
read_mmmc ../scripts/syn_mmmc.tcl

# Timing libraries must exist before LEF unit synchronization.
set_db lef_library $tech(lef_list)

# read RTL in filelist
read_hdl -language sv -f $log_syn(sv_list)

# compile RTL source
# if top module is parameterized, set here
elaborate $log_syn(design)

# initialize the database for execution
init_design -top $log_syn(design)

# report message for RTL elaborate
report_messages > $log_syn(reports_path)/runtime/elaborate_message.rpt


# -----------------------------------------------------------------------------------
# Set Synthesis Optimization
# -----------------------------------------------------------------------------------
# "vfind . -design *" means find any "design" type object under current directory
# Genus creates a "cost group" for each clock defined in SDC
# create a cost group for the paths going through clock gate enable pins
set_db [vfind . -design *] .lp_clock_gating_auto_cost_grouping true

# control automatic timing adjustment on the clock gate enable paths
# possible value: fixed | none | variable
# fixed: use the user-defined path adjust value
# variable: scale the tool-calculated path adjust values
set_db [vfind . -design *] .lp_clock_gating_auto_path_adjust variable

# cell path to be used for clock-gating insertion
# Leave unset to let Genus select suitable ICG cells.
# set cg_cell_list $rm_clock_icg_cell
# puts "ICG cells selected: $cg_cell_list"
# set_db [vfind . -design *] \
#     .lp_clock_gating_cell $cg_cell_list

# total power = w * leakage + (1-w) * dynamic
# max_leakage_power & max_dynamic_power must be set
set_db [vfind . -module $log_syn(design)] .lp_power_optimization_weight 0.5

# prune logic that does not drive any loads
set_db [vfind . -hpin *] .prune_unused_logic false

# allow constant propagation through sequential instance
# thus allow removal of the instance
# possible value: false | inherited | true
# inherited: inherit the value of optimize_constant_[0|1]_[flops|latches] root attribute
set_db [vfind . -inst *] .optimize_constant_0_seq   inherited
set_db [vfind . -inst *] .optimize_constant_1_seq   inherited

# allow merging with other equivalent
# possible value: false | inherited | true
# inherited: inherit the value of optimize_merge_[flops|latches] root attribute
set_db [vfind . -inst *] .optimize_merge_seq        inherited

# allow optimization going outside module
# flatten hierarchy of original design
# possible value: false | strict_no | true
# default: true
set_db [vfind . -module *] .boundary_opto false

# allow retiming for improving performance of sequential circuits
# default: false
set_db [vfind . -design *] .retime false

# create floorplan for physical-aware synthesis
# set_db physical_aware_multibit_mapping auto
# create_floorplan -core_box {0 0 1000 1000} $log_syn(design)

# create path for reports
exec mkdir -p $log_syn(reports_path)/power
exec mkdir -p $log_syn(reports_path)/timing
exec mkdir -p $log_syn(reports_path)/area
exec mkdir -p $log_syn(reports_path)/runtime
exec mkdir -p $log_syn(reports_path)/time_intent
exec mkdir -p $log_syn(reports_path)/others
