# Rebuild the CURRENT RTL, with empty SRAM, for the Lab6 A7-35T board.
# vivado -mode batch -source fpga/demo/build_bitstream.tcl -tclargs OUTPUT_DIR
set here [file normalize [file dirname [info script]]]
set root [file normalize [file join $here ../..]]
if {[llength $argv] != 1} {error "Pass a fresh output directory"}
set out [file normalize [lindex $argv 0]]
if {[file exists [file join $out live_demo.xpr]]} {error "Use a fresh build directory"}
file mkdir $out
set_param general.maxThreads 4
create_project live_demo $out -part xc7a35tcsg324-1 -force
set_property target_language Verilog [current_project]
set includes {}
set fd [open [file join $root rtl/filelist.f] r]
foreach line [split [read $fd] \n] {
    set line [string trim $line]
    if {$line eq "" || [string match {//*} $line]} {continue}
    if {[string match {+incdir+*} $line]} {
        lappend includes [file normalize [file join $root [string range $line 8 end]]]
    } else {
        add_files -norecurse [file join $root $line]
    }
}
close $fd
set_property include_dirs $includes [get_filesets sources_1]
add_files -norecurse [file join $root fpga/fpga_top.sv]
add_files -fileset constrs_1 -norecurse [file join $root fpga/fpga_top.xdc]
set_property top fpga_top [get_filesets sources_1]
create_ip -name clk_wiz -vendor xilinx.com -library ip -module_name clk_wiz_0
set_property -dict [list CONFIG.PRIM_IN_FREQ {100.000} \
    CONFIG.CLKOUT1_REQUESTED_OUT_FREQ {20.000} CONFIG.USE_RESET {false} \
    CONFIG.USE_LOCKED {true}] [get_ips clk_wiz_0]
set_property generate_synth_checkpoint false [get_files -all */clk_wiz_0.xci]
generate_target all [get_ips clk_wiz_0]
update_compile_order -fileset sources_1
# The top's default SRAM_INIT_FILE is empty: real Debug SBA loads it once.
synth_design -top fpga_top -part xc7a35tcsg324-1 -directive AreaOptimized_high
write_checkpoint -force [file join $out synthesized.dcp]
report_utilization -file [file join $out utilization_synth.rpt]
opt_design
place_design -directive Explore
phys_opt_design
route_design -directive Explore
# Vivado 2019.1 infers post-route operation from the current design state.
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
puts $fd "PASS current RTL; empty SRAM; part=xc7a35tcsg324-1; clock=20MHz; setup=$wns hold=$whs"
close $fd
close_project
