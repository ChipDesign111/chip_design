# Fallback build that avoids the Windows cscript launch wrapper used by
# launch_runs. Run from any directory with Vivado in batch mode.
set script_dir [file normalize [file dirname [info script]]]
set project_file [file join $script_dir final_project final_project.xpr]
set top_file [file join $script_dir fpga_top.sv]
set constraint_file [file join $script_dir fpga_top.xdc]
set init_file [file join $script_dir firmware int8_selftest.hex]
set build_dir [file join $script_dir final_project final_project.runs direct]

open_project $project_file
file mkdir $build_dir
cd $build_dir

synth_design -top fpga_top -part xc7a35tcsg324-1 -directive AreaOptimized_high \
    -generic "SRAM_INIT_FILE=$init_file"
read_xdc $constraint_file
opt_design
place_design
route_design

write_checkpoint -force [file join $build_dir fpga_top_routed.dcp]
report_utilization -file [file join $build_dir utilization.rpt]
report_timing_summary -file [file join $build_dir timing_summary.rpt]
report_drc -file [file join $build_dir drc.rpt]
write_bitstream -force [file join $build_dir fpga_top.bit]

close_project
