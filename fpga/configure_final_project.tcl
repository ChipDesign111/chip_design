# Add the FPGA board top and Lab6-compatible constraints to the existing project.
set script_dir [file normalize [file dirname [info script]]]
set project_file [file join $script_dir final_project final_project.xpr]
set top_file [file join $script_dir fpga_top.sv]
set constraint_file [file join $script_dir fpga_top.xdc]
set fp_wrapper_file [file normalize [file join $script_dir .. rtl cpu_cv32e40p rtl cv32e40p_fp_wrapper.sv]]

open_project $project_file

if {[llength [get_files -quiet $top_file]] == 0} {
    add_files -fileset sources_1 -norecurse $top_file
}
set_property file_type SystemVerilog [get_files $top_file]
set_property used_in_simulation true [get_files $top_file]
set_property used_in_synthesis true [get_files $top_file]
set_property used_in_implementation true [get_files $top_file]

if {[llength [get_files -quiet $constraint_file]] == 0} {
    add_files -fileset constrs_1 -norecurse $constraint_file
}

# The SoC fixes FPU=0 and does not carry the FPnew package sources.
if {[llength [get_files -quiet $fp_wrapper_file]] != 0} {
    remove_files [get_files $fp_wrapper_file]
}

set_property top fpga_top [get_filesets sources_1]
set_property top_file $top_file [get_filesets sources_1]
set_property top_auto_set FALSE [get_filesets sources_1]
update_compile_order -fileset sources_1

# Favor turnaround time while bringing up the board. The final release can
# switch back to a performance-oriented strategy.
set_property strategy Flow_RuntimeOptimized [get_runs synth_1]
set_property -name {STEPS.SYNTH_DESIGN.ARGS.DIRECTIVE} \
    -value RuntimeOptimized -objects [get_runs synth_1]
set_property -name {STEPS.SYNTH_DESIGN.ARGS.FLATTEN_HIERARCHY} \
    -value none -objects [get_runs synth_1]

close_project
