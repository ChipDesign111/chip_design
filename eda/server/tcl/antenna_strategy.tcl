# Native geometry repair only. Never delete a diode or modify library rules.
proc eda_apply_antenna_strategy {} {
    global eda_antenna_repair_strategy
    set allow [expr {$eda_antenna_repair_strategy ne "native_jumpers_first"}]
    setNanoRouteMode -routeInsertAntennaDiode $allow -drouteFixAntenna true
    set actual [expr {[getNanoRouteMode -routeInsertAntennaDiode] ? 1 : 0}]
    if {$actual != $allow || ![getNanoRouteMode -drouteFixAntenna]} {
        error "Native antenna repair strategy readback mismatch"
    }
    puts "EDA_NATIVE_ANTENNA strategy=$eda_antenna_repair_strategy initial_diodes=$allow jumping=true"
}

proc eda_antenna_nets {report} {
    set fd [open $report r];set txt [read $fd];close $fd
    if {[string first "No Violations Found" $txt] >= 0} {return {}}
    set nets {}
    foreach line [split $txt "\n"] {
        if {[regexp {^(\S+) \([0-9]+\)$} [string trimright $line] -> net]} {lappend nets $net}
    }
    set nets [lsort -unique $nets]
    if {![regexp {Number of nets violated:\s+([0-9]+)} $txt -> count] || [llength $nets] != $count} {
        error "Unrecognized native antenna report/net-count mismatch: $report"
    }
    return $nets
}

proc eda_native_antenna_repair {prefix} {
    file mkdir [file dirname $prefix]
    set code [catch {
        set attempt 0
        # First prefer native layer jumping. Only remaining independently
        # reported violations may receive native diode fallback.
        foreach allow {false false true} {
            set report ${prefix}_${attempt}.rpt
            verifyProcessAntenna -report $report
            set nets [eda_antenna_nets $report]
            if {[llength $nets] == 0} {break}
            setNanoRouteMode -routeInsertAntennaDiode $allow -drouteFixAntenna true
            puts "EDA_NATIVE_ANTENNA_REPAIR attempt=$attempt allow_diodes=$allow nets=$nets"
            deselectAll
            foreach net $nets {selectNet $net}
            detailRoute -select
            deselectAll
            incr attempt
        }
        verifyProcessAntenna -report ${prefix}_final.rpt
    } result options]
    deselectAll
    eda_apply_antenna_strategy
    return -options $options $result
}
