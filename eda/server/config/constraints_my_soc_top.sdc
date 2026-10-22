#############################################################################
# Description:  Synopsys Design Constraints
# Modifier:     Mingxuan Li <mingxuanli_siris@163.com> [Peking University]
# Acknowledge:  Columbia University, System Level Design Group
#############################################################################

set_units -time ns -capacitance pF

# -------------------------------------------
# Timing Constraints
# -------------------------------------------
# set $rm_clock_pin to name "clk", no need to be the same
# "clk" will be referred as clock pin by tools
# "get_ports" is aliased as "get_port", return full path to specified port
# if clk is generated inside module, use "get_pins" instead
# refer to pin name hierachically, for example: a_inst/b_inst/clk_i
create_clock -period 100 \
    -waveform {0 50} \
    -name jtag_clk \
    [get_ports tck_i]

create_clock -period ${rm_clock_period} \
    -waveform [list 0 [expr ${rm_clock_period}/2.0]] \
    -name sys_clk \
    [get_ports clk_i]




# set virtual clk for I/O port
# to model IO delays relative to a top level clk
create_clock -period 1000 -waveform {0 500}     -name virtual_jtag_tck


set sys_clk_list        [list sys_clk]
set jtag_clk_list       [list jtag_clk]
set all_clk_list        [concat ${sys_clk_list} ${jtag_clk_list}]
set virtual_clk_list    [list virtual_jtag_tck]

# apply to all clocks in the fanout and corresponding sequential logic of the port
# "get_clocks" is aliased as "get_clock", return full path of clock name defined of "create_clock"
foreach clk_member ${all_clk_list} {
    set_clock_uncertainty -setup    [expr ${rm_pre_cts_clock_uncertainty} + ${rm_setup_margin} + ${rm_period_jitter}] [get_clocks ${clk_member}]
    set_clock_uncertainty -hold     [expr ${rm_hold_margin}]                                                          [get_clocks ${clk_member}]
}
foreach vclk_member ${virtual_clk_list} {
    set_clock_uncertainty -setup    [expr ${rm_pre_cts_clock_uncertainty} + ${rm_period_jitter}] [get_clocks ${vclk_member}]
    set_clock_uncertainty -hold     [expr ${rm_pre_cts_clock_uncertainty} + ${rm_period_jitter}] [get_clocks ${vclk_member}]
}


# define IO constraints using virtual clock
set_input_delay  0 \
    -clock virtual_jtag_tck \
    [get_ports tms_i]

set_input_delay  0 \
    -clock virtual_jtag_tck \
    [get_ports td_i]

set_output_delay 0 \
    -clock virtual_jtag_tck \
    -clock_fall \
    [get_ports td_o]


# define asynchronous clock groups, i.e. "set_false_path" to clock
# -allow_paths: allow paths between asynchronous clock groups to be traced in timing analysis
set_clock_groups -asynchronous -group ${sys_clk_list} -group [concat ${jtag_clk_list} virtual_jtag_tck] -allow_paths

# clock-domain-crossing constraints
set eda_async_nets [get_nets -hierarchical async*]
if {[sizeof_collection $eda_async_nets] > 0} {
  set_max_delay [expr 0.6*$rm_clock_period] -through $eda_async_nets -ignore_clock_latency
  set_false_path -hold -through $eda_async_nets
}

# path exceptions

# exclude path for timing analysis
set input_false_path_list  [list rst_ni]
# set output_false_path_list [list clk_led_pad]

foreach input_false_path ${input_false_path_list} {
    set_false_path -from [get_ports ${input_false_path}]
}
# foreach output_false_path ${output_false_path_list} {
#     set_false_path -to   [get_ports ${output_false_path}]
# }


# allow resizing a mapped module or child instance during optimization, but not deleting, renaming, or remapping it


# -------------------------------------------
# Design Rule Constraints
# -------------------------------------------
# specify capacitance on specified ports

# set maximum fanout load limit constraints on whole design
set_max_fanout ${rm_max_fanout} ${rm_core_top}

# specify maximum transition for whole design
# override clock maximum transition
# set_max_transition ${rm_max_transition} ${rm_core_top}
# set_max_transition ${rm_max_clock_transition} [get_clocks] -clock_path
