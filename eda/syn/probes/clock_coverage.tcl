# Read-only audit of a saved mapped database. No optimization or exports.
# Run from the original saved-design working directory. COVERAGE_SETUP is the
# generated genus_setup.tcl; COVERAGE_INTENT is its saved timing-intent report.
source $::env(COVERAGE_SETUP)
report_timing -max_paths 1 -views func_tt > /dev/null
set fh [open $::env(COVERAGE_INTENT) r]
set text [read $fh]
close $fh
set section 0
set count 0
array set values {}
foreach line [split $text "\n"] {
    if {[string match {Sequential clock pins without clock waveform*} $line]} {
        set section 1
        continue
    }
    if {$section && [string match {Timing exceptions with no effect*} $line]} {break}
    if {!$section || ![regexp {^pin:my_soc_top/(.+)$} $line -> name]} {continue}
    set object [get_pins $name]
    set value [get_db $object .timing_case_computed_value]
    puts "CLOCK_COVERAGE $name value=$value"
    if {![info exists values($value)]} {set values($value) 0}
    incr values($value)
    incr count
}
puts "CLOCK_COVERAGE_COUNT $count"
foreach value [lsort [array names values]] {
    puts "CLOCK_COVERAGE_VALUE $value count=$values($value)"
}
if {[info exists ::env(COVERAGE_GATES)]} {
    source $::env(COVERAGE_GATES)
    foreach name $inactive_gate_enable_pins {
        set object [get_pins $name]
        puts "CLOCK_GATE_ENABLE $name computed=[get_db $object .timing_case_computed_value]"
    }
}
if {[info exists ::env(COVERAGE_AUDIT_ROOT)]} {
    set audit_root $::env(COVERAGE_AUDIT_ROOT)
    report_timing -from [get_clocks jtag_clk] -to [get_clocks sys_clk] -max_paths 10 -views func_tt > $audit_root/cdc_jtag_to_sys.rpt
    report_timing -from [get_clocks sys_clk] -to [get_clocks jtag_clk] -max_paths 10 -views func_tt > $audit_root/cdc_sys_to_jtag.rpt
    puts "CLOCK_CROSSING_REPORTS_FINISHED"
}
puts "CLOCK_COVERAGE_FINISHED"
exit
