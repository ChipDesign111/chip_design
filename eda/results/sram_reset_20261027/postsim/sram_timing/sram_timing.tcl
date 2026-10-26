# Supplemental read-only STA from the same final database used by SDF.
# The caller supplies eda_work and timing_output. Never save/ECO this design.
setMultiCpuUsage -localCpu 1
source [file join $eda_work pnr my_soc_top backup step34.enc]
file mkdir $timing_output
set macro i_mainmem/i_sram/i_macro
if {[sizeof_collection [get_cells $macro]] != 1} {error "Expected one native main SRAM"}
set inputs [get_pins [list ${macro}/A* ${macro}/D* ${macro}/WEN* ${macro}/CEN]]
set outputs [get_pins ${macro}/Q*]
if {[sizeof_collection $inputs] != 48 || [sizeof_collection $outputs] != 32} {
    error "Unexpected native SRAM port widths"
}
report_clocks > [file join $timing_output clocks.log]
report_timing -late -to $inputs -max_paths 20 -path_type full_clock > [file join $timing_output sram_input_setup.log]
report_timing -early -to $inputs -max_paths 20 -path_type full_clock > [file join $timing_output sram_input_hold.log]
report_timing -late -from $outputs -max_paths 20 -path_type full_clock > [file join $timing_output sram_output_setup.log]
report_timing -early -from $outputs -max_paths 20 -path_type full_clock > [file join $timing_output sram_output_hold.log]
puts "SRAM_PORT_TIMING_REPORTED_NO_ECO"
exit 0
