# Native Innovus uses -T; Genus Common UI uses -temperature.
# Read actual values after creation AND every checkpoint restore. Do not
# silently re-bless or change a restored database with the wrong temperature.
proc eda_check_rc_temperatures {} {
    global eda_work proj
    set fields {}
    foreach corner $proj(corners) {
        set actual [get_rc_corner rc_${corner} -T]
        set expected $proj($corner,T)
        if {![string is double -strict $actual] || abs($actual-$expected)>0.000001} {
            error "RC temperature mismatch rc_${corner}: actual=$actual expected=$expected"
        }
        lappend fields [format {"%s":%g} $corner $actual]
        puts "EDA_RC_TEMPERATURE rc_${corner} actual=$actual expected=$expected"
    }
    set fd [open [file join $eda_work evidence rc_temperatures.json] w]
    puts $fd "\{[join $fields ,]\}"
    close $fd
}
