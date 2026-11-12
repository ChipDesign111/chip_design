# Report-driven, non-inverting buffer split for ordinary single-driver nets.
# Innovus 21.16 disables automatic fanout fixing in optDesign -postRoute.
# Source syntax: installed innovusTCR/ecoAddRepeater.html and setEcoMode.html.
proc eda_literal_net_pattern {name} {
    regsub -all {[][\\.^$*+?(){}|]} $name {\\&} escaped
    return "^${escaped}$"
}
proc eda_db_string {value} {
    while {[llength $value] == 1} {
        set unwrapped [lindex $value 0]
        if {$unwrapped eq $value} {break}
        set value $unwrapped
    }
    return $value
}
proc eda_choose_fanout_terms {receivers} {
    set logical {}
    foreach row $receivers {
        # Keep existing antenna protection on the original driver net.
        if {![string match ANTENNA* [lindex $row 3]]} {lappend logical $row}
    }
    if {[llength $logical] < 2} {error "Fanout ECO needs at least two ordinary input pins"}
    set logical [lsort -real -index 0 $logical]
    set chosen {}
    foreach row [lrange $logical 0 [expr {[llength $logical]/2-1}]] {lappend chosen [lindex $row 2]}
    return $chosen
}
proc eda_fix_fanout {directory} {
    global eda_work eda_python eda_fanout_targets eda_fanout_serial
    puts [exec $eda_python [file join $eda_work flow bin flow.py] fanout-plan --work $eda_work --directory $directory]
    set fd [open [file join $eda_work pnr generated 32_fanout_plan.tcl] r]
    set body [read $fd]; close $fd
    eda_eval 32_fanout_plan $body
    if {[llength $eda_fanout_targets] == 0} {return 0}
    if {![info exists eda_fanout_serial]} {set eda_fanout_serial 0}
    eda_eval 32_eco_mode {setEcoMode -reset; setEcoMode -LEQCheck true -refinePlace false -updateTiming false}
    foreach target $eda_fanout_targets {
        lassign $target net_name driver_name maximum actual
        set net [dbGet -e -regexp top.nets.name [eda_literal_net_pattern $net_name] -p]
        if {[llength $net] != 1 || $net in {{} 0x0}} {error "Fanout net not uniquely resolved: $net_name count=[llength $net]"}
        set actual_net_name [eda_db_string [dbGet $net.name]]
        if {$actual_net_name ne $net_name} {error "Fanout net name mismatch: report=$net_name actual=$actual_net_name"}
        if {[dbGet $net.isPwrOrGnd] || [dbGet $net.isClock] || [dbGet $net.isCTSClock] || [llength [dbGet -e $net.terms]]} {
            error "Refuse automatic ECO on supply/clock/external net: $net_name"
        }
        set receivers {}; set drivers {}; set original_inputs {}
        foreach it [dbGet $net.instTerms] {
            if {[dbGet $it.isInput] && [dbGet $it.isOutput]} {error "Bidirectional fanout pin requires manual adaptation"}
            set pin_name [eda_db_string [dbGet $it.name]]
            if {[dbGet $it.isOutput]} {lappend drivers $pin_name}
            if {[dbGet $it.isInput]} {
                lassign [lindex [dbGet $it.pt] 0] x y
                set cell_name [eda_db_string [dbGet $it.inst.cell.name]]
                lappend receivers [list $x $y $pin_name $cell_name]
                lappend original_inputs [list $it $pin_name $cell_name]
            }
        }
        if {[llength $drivers] != 1} {error "Fanout net must have exactly one output driver: $net_name drivers=$drivers"}
        set actual_driver [lindex $drivers 0]
        if {$actual_driver ne $driver_name} {
            # Report generation and the ECO database can differ after an earlier
            # timing/DRV repair. The unique live driver is authoritative.
            puts "EDA_FANOUT_DRIVER_REFRESH net=$net_name report=$driver_name actual=$actual_driver"
        }
        if {[llength $receivers] <= $maximum} {
            puts "EDA_FANOUT_ALREADY_FIXED net=$net_name load=[llength $receivers] limit=$maximum"
            continue
        }
        set selected [eda_choose_fanout_terms $receivers]
        while {1} {
            incr eda_fanout_serial
            set name [format EDA_FANOUT_%04d $eda_fanout_serial]
            if {![llength [dbGet -e top.insts.name *$name]]} {break}
        }
        # LEQCheck stays enabled; a single BUFFD2 is non-inverting.
        set command [list ecoAddRepeater -term [join $selected " "] -cell BUFFD2BWP7T -name $name]
        set result [eda_eval 32_fanout_split $command]
        if {[llength $result] != 3} {error "Expected one non-inverting ECO buffer"}
        lassign $result new_instance input_net output_net
        set new_instance [eda_db_string $new_instance]
        set input_net [eda_db_string $input_net]
        set output_net [eda_db_string $output_net]
        if {$input_net ne $net_name || $output_net eq $net_name} {
            error "Unexpected fanout ECO net split: report=$net_name input=$input_net output=$output_net"
        }
        foreach pin $original_inputs {
            lassign $pin object original_name cell_name
            set expected [expr {$original_name in $selected ? $output_net : $input_net}]
            set actual_net [eda_db_string [dbGet $object.net.name]]
            if {$actual_net ne $expected} {
                if {[string match ANTENNA* $cell_name]} {
                    puts "EDA_FANOUT_ANTENNA_MOVED net=$net_name pin=$original_name from=$expected to=$actual_net"
                    continue
                }
                error "Fanout ECO sink mismatch: pin=$original_name expected=$expected actual=$actual_net"
            }
        }
        puts "EDA_FANOUT_SPLIT net=$net_name driver=$actual_driver old_load=[llength $receivers] limit=$maximum moved=[llength $selected] original_inputs=[llength $original_inputs] buffer=$new_instance new_net=$output_net"
    }
    eda_eval 32_eco_legalize {globalNetConnect VDD -type pgpin -pin VDD -all; globalNetConnect VSS -type pgpin -pin VSS -all; refinePlace}
    eda_eval 32_eco_route {ecoRoute}
    eda_eval 32_eco_reset {setEcoMode -reset}
    eda_eval 32_eco_extract {extractRC}
    eda_eval 32_eco_setup {timeDesign -postRoute -expandedViews -outDir ../my_soc_top/reports/postRoute_fanout_check}
    eda_eval 32_eco_hold {timeDesign -postRoute -hold -expandedViews -outDir ../my_soc_top/reports/postRoute_fanout_check}
    return [llength $eda_fanout_targets]
}
