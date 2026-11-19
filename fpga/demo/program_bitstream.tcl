# vivado -mode batch -source fpga/demo/program_bitstream.tcl -tclargs BITFILE
set here [file normalize [file dirname [info script]]]
if {[llength $argv] != 1} {error "Pass the newly built bitstream path"}
open_hw
source [file join $here ../connect_fpga.tcl]
har_program_fpga [file normalize [lindex $argv 0]]
close_hw
