# Report post-synthesis resource use by hierarchy.
set script_dir [file normalize [file dirname [info script]]]
set checkpoint [file join $script_dir final_project final_project.runs synth_1 fpga_top.dcp]
set report [file join $script_dir final_project final_project.runs synth_1 fpga_top_hierarchical_utilization.rpt]

open_checkpoint $checkpoint
report_utilization -hierarchical -hierarchical_depth 6 -file $report
close_design
