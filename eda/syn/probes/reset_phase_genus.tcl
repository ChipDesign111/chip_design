# Independent small-circuit synthesis. No production RTL or checkpoint read.
source $::env(PROBE_CONFIG)
set_db max_cpus_per_server 1
set_db information_level 3
read_libs $std_lib
read_hdl -language sv -f probe.f
elaborate reset_phase_probe
set_units -time ns -capacitance pF
create_clock -name root_clock -period 20 [get_ports clk_i]
create_clock -name payload_clock -period 20 -waveform {0.12 10.12} [get_ports payload_clk_i]
set_input_transition 0.5 [all_inputs]
set_load 0.2 [get_ports counter*]
set_false_path -from [get_ports raw_reset_ni]
set_db lp_insert_clock_gating false
set_db [vfind . -design *] .retime false
syn_generic reset_phase_probe
syn_map reset_phase_probe
syn_opt reset_phase_probe -incremental
write_hdl -language v2001 > mapped.v
write_sdf -timescale ps > mapped.sdf
report_units > units.rpt
puts "RESET_PHASE_SYNTHESIS_FINISHED"
exit
