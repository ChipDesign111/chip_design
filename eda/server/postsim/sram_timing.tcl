# Supplemental read-only STA from the same final database used by SDF.
# The caller supplies eda_work and timing_output. Never save/ECO this design.
setMultiCpuUsage -localCpu 8
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
# The new common transaction-reset boundary is clocked on falling edges.
# Report its real half-cycle path into the rising-edge SRAM command register
# in every active library view, without changing any clock/path constraint.
if {[file exists [file join $eda_work src chip_design rtl memory sram_transaction_reset.sv]]} {
    set qualified_reset [get_cells -hierarchical *i_sram_transaction_reset*reset_qualified_n_reg*]
    if {[sizeof_collection $qualified_reset] != 1} {error "Expected one common SRAM transaction-reset output register"}
    set request_d [get_pins i_mainmem/port_req_q_reg/D]
    if {[sizeof_collection $request_d] != 1} {error "Expected one SRAM request register D pin"}
    set reset_views [all_analysis_views -type setup]
    foreach view $reset_views {
        report_timing -late -view $view -from $qualified_reset -to $request_d -max_paths 10 -path_type full_clock > [file join $timing_output reset_to_request_${view}_setup.log]
        report_timing -early -view $view -from $qualified_reset -to $request_d -max_paths 10 -path_type full_clock > [file join $timing_output reset_to_request_${view}_hold.log]
    }
    puts "SHARED_SRAM_RESET_TIMING_REPORTED_NO_EXCEPTION"
}
puts "SRAM_PORT_TIMING_REPORTED_NO_ECO"
exit 0
