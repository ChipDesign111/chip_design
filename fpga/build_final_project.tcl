# Build the existing final_project, optionally stopping after synthesis.
set script_dir [file normalize [file dirname [info script]]]
set project_file [file join $script_dir final_project final_project.xpr]
set build_bitstream [expr {[lindex $argv 0] ne "synth"}]

open_project $project_file
set_property strategy Flow_RuntimeOptimized [get_runs synth_1]
set_property -name {STEPS.SYNTH_DESIGN.ARGS.DIRECTIVE} \
    -value RuntimeOptimized -objects [get_runs synth_1]
set_property -name {STEPS.SYNTH_DESIGN.ARGS.FLATTEN_HIERARCHY} \
    -value none -objects [get_runs synth_1]
reset_run synth_1
launch_runs synth_1 -jobs 1
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} {
    error "Synthesis failed; inspect final_project.runs/synth_1"
}

if {$build_bitstream} {
    set_property strategy Flow_RuntimeOptimized [get_runs impl_1]
    reset_run impl_1
    launch_runs impl_1 -to_step write_bitstream -jobs 1
    wait_on_run impl_1
    if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} {
        error "Implementation failed; inspect final_project.runs/impl_1"
    }
}

close_project
