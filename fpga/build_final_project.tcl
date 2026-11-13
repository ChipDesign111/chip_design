# Build the existing final_project, optionally stopping after synthesis.
set script_dir [file normalize [file dirname [info script]]]
set project_file [file join $script_dir final_project final_project.xpr]
set top_file [file join $script_dir fpga_top.sv]
set init_file [file join $script_dir firmware int8_selftest.hex]
set build_bitstream [expr {[lindex $argv 0] ne "synth"}]

open_project $project_file
set_property strategy Flow_AreaOptimized_high [get_runs synth_1]
set_property -name {STEPS.SYNTH_DESIGN.ARGS.DIRECTIVE} \
    -value AreaOptimized_high -objects [get_runs synth_1]
set_property -name {STEPS.SYNTH_DESIGN.ARGS.MORE OPTIONS} \
    -value [list -generic [list SRAM_INIT_FILE=$init_file]] -objects [get_runs synth_1]
reset_run synth_1
launch_runs synth_1 -jobs 1
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {
    error "Synthesis failed; inspect final_project.runs/synth_1"
}

if {$build_bitstream} {
    set_property strategy "Vivado Implementation Defaults" [get_runs impl_1]
    reset_run impl_1
    launch_runs impl_1 -to_step write_bitstream -jobs 1
    wait_on_run impl_1
    if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {
        error "Implementation failed; inspect final_project.runs/impl_1"
    }
}

close_project
