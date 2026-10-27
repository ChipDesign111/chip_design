#####################################################################################
# Description:  User-Specific Definition file
# Author:       Mingxuan Li <mingxuanli_siris@163.com> [Peking University]
#####################################################################################

# Top module name
# ONLY ONE SPACE between 'rm_core_top' keyword and module name!
set rm_core_top my_soc_top
set rm_clock_period 20
set eda_opt_max_density 0.85

set PROJECT_ROOT {}
set PDK_ROOT /lec/pdk/tsmc180
# List the names of the MACROs instantiated in design
# Directory format: src/macro/<name>/
# Dont comment this variable
# If no extra macro instances, leave a blank list
# ONLY ONE SPACE bwtween 'list' keyword and macro name!
set macro_insts [list RA1SHD_2048x32M8]

# ONLY ONE SPACE bwtween 'std_lib' keyword and std_lib name!
set std_lib tcb018gbwp7t
set cell_ext [list BWP7T]

# Specify active analysis view for timing analysis
# The variable values format must be func_<corner>
# possible func_<corner> value:
# func_tt_1p80v_25c
set proj(analysis_view,setup) "func_tt_1p80v_25c"
set proj(analysis_view,hold)  "func_tt_1p80v_25c"

# This flow supplies the standard synthesis profile.
set syn_opt_level standard

# This flow supplies the standard physical implementation profile.
set pnr_opt_level standard

# Multi-CPU setting
# prepare writes the CPU allocation selected in design.json.
set syn_cpus 8
set pnr_cpus 8

# Power net name
set init_gnd_net {VSS}
set init_pwr_net {VDD}

# Routing layer
# Possible value: METAL1 | METAL2 | METAL3 | METAL4 | METAL5 | METAL6
# M1 is NOT RECOMMENDED for routing
set topRoutingLayer     METAL6
set bottomRoutingLayer  METAL2
