# Resume an already completed synthesis without repeating it.
# vivado -mode batch -source fpga/demo/implement_checkpoint.tcl -tclargs BUILD_DIR
if {[llength $argv] != 1} {error "Pass the build directory containing synthesized.dcp"}
set out [file normalize [lindex $argv 0]]
set_param general.maxThreads 4
open_checkpoint [file join $out synthesized.dcp]
opt_design
place_design -directive Explore
phys_opt_design
route_design -directive Explore
phys_opt_design
write_checkpoint -force [file join $out routed.dcp]
report_utilization -file [file join $out utilization.rpt]
report_timing_summary -file [file join $out timing_summary.rpt]
report_route_status -file [file join $out route_status.rpt]
report_drc -file [file join $out drc.rpt]
set setup [get_timing_paths -delay_type max -max_paths 1]
set hold [get_timing_paths -delay_type min -max_paths 1]
if {[llength $setup] == 0 || [llength $hold] == 0} {error "No timing paths"}
set wns [get_property SLACK $setup]
set whs [get_property SLACK $hold]
if {$wns < 0 || $whs < 0} {error "Timing failed: setup=$wns hold=$whs"}
write_bitstream -force [file join $out fpga_top.bit]
set fd [open [file join $out build_status.txt] w]
puts $fd "PASS current RAW RTL; empty SRAM; part=xc7a35tcsg324-1; clock=20MHz; setup=$wns hold=$whs"
close $fd
close_design
