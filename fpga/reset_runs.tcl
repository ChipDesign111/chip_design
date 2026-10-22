# Clear stale or canceled synthesis/implementation run state.
set script_dir [file normalize [file dirname [info script]]]
set project_file [file join $script_dir final_project final_project.xpr]

open_project $project_file
reset_run synth_1
reset_run impl_1
close_project
