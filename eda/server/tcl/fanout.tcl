# Report-driven, non-inverting buffer split for ordinary single-driver nets.
# Innovus 21.16 disables automatic fanout fixing in optDesign -postRoute.
# Source syntax: installed innovusTCR/ecoAddRepeater.html and setEcoMode.html.
proc eda_literal_net_pattern {name} {
    regsub -all {[][\\.^$*+?(){}|]} $name {\\&} escaped
    return "^${escaped}$"
}
proc eda_choose_fanout_terms {receivers} {
    set logical {}
    foreach row $receivers {
        # Keep existing antenna and delay protection on the original driver net.
        if {![string match ANTENNA* [lindex $row 3]] && ![string match DEL* [lindex $row 3]]} {lappend logical $row}
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
        if {[llength $net] != 1 || $net in {{} 0x0} || [dbGet $net.name] ne $net_name} {error "Fanout net not uniquely resolved: $net_name"}
        if {[dbGet $net.isPwrOrGnd] || [dbGet $net.isClock] || [dbGet $net.isCTSClock] || [llength [dbGet -e $net.terms]]} {
            error "Refuse automatic ECO on supply/clock/external net: $net_name"
        }
        set receivers {}; set drivers {}; set original_inputs {}
        foreach it [dbGet $net.instTerms] {
            if {[dbGet $it.isInput] && [dbGet $it.isOutput]} {error "Bidirectional fanout pin requires manual adaptation"}
            if {[dbGet $it.isOutput]} {lappend drivers [dbGet $it.name]}
            if {[dbGet $it.isInput]} {
                lassign [lindex [dbGet $it.pt] 0] x y
                lappend receivers [list $x $y [dbGet $it.name] [dbGet $it.inst.cell.name]]
                lappend original_inputs [list $it [dbGet $it.name] [dbGet $it.inst.cell.name]]
            }
        }
        if {[llength $drivers] != 1 || [lindex $drivers 0] ne $driver_name} {error "Fanout driver differs from current report"}
        set selected [eda_choose_fanout_terms $receivers]
        while {1} {
            incr eda_fanout_serial
            set name [format EDA_FANOUT_%04d $eda_fanout_serial]
            if {![llength [dbGet -e top.insts.name *$name]]} {break}
        }
        # LEQCheck stays enabled; a single BUFFD2 is non-inverting.
        set command [list ecoAddRepeater -term $selected -cell BUFFD2BWP7T -name $name]
        set result [eda_eval 32_fanout_split $command]
        # Resolve the inserted buffer from the database by the name that was
        # requested; the command's return value is informational only, since
        # its formatting is not part of the documented interface.
        set new_instance ""
        set hits [dbGet -e top.insts.name *$name]
        if {[llength $hits] == 1} {
            set new_instance [lindex $hits 0]
        } elseif {[llength $result] == 3} {
            set candidate [lindex $result 0]
            if {[llength [dbGet -e -regexp top.insts.name [eda_literal_net_pattern $candidate] -p]] == 1} {set new_instance $candidate}
        }
        if {$new_instance eq ""} {error "Fanout ECO buffer not found in database: $name"}
        if {[llength $result] != 3 || [lindex $result 0] ne $new_instance} {
            puts "EDA_FANOUT_NOTE net=$net_name eco_return=$result buffer=$new_instance"
        }
        # ECO commands may recreate the instances they touch, so the instTerm
        # handles collected before the split cannot be trusted afterwards.
        # Verify against the connectivity the database reports now, resolved by
        # name: the driver's own pins tell which net is which, independently of
        # how the command's return value is formatted.
        set inst [dbGet -e -regexp top.insts.name [eda_literal_net_pattern $new_instance] -p]
        if {[llength $inst] != 1} {error "Fanout ECO buffer not uniquely resolved: $new_instance"}
        set in_pin {}; set out_pin {}
        foreach it [dbGet $inst.instTerms] {
            set pin_name [dbGet $it.name]
            if {$pin_name eq "$new_instance/I"} {lappend in_pin $it}
            if {$pin_name eq "$new_instance/Z"} {lappend out_pin $it}
        }
        if {[llength $in_pin] != 1 || [llength $out_pin] != 1} {
            error "Fanout ECO buffer pins not uniquely resolved: $new_instance ($in_pin $out_pin)"
        }
        set input_net_now  [dbGet [lindex $in_pin 0].net.name]
        set output_net_now [dbGet [lindex $out_pin 0].net.name]
        if {$input_net_now ne $net_name || $output_net_now eq $net_name || $output_net_now eq ""} {
            error "Unexpected fanout ECO net split: buffer=$new_instance in=$input_net_now out=$output_net_now"
        }
        set in_net [dbGet -e -regexp top.nets.name [eda_literal_net_pattern $input_net_now] -p]
        set out_net [dbGet -e -regexp top.nets.name [eda_literal_net_pattern $output_net_now] -p]
        if {[llength $in_net] != 1 || [llength $out_net] != 1} {error "Fanout ECO nets not uniquely resolved: $input_net_now $output_net_now"}
        set in_terms {}
        foreach it [dbGet $in_net.instTerms] {lappend in_terms [dbGet $it.name]}
        set out_terms {}
        foreach it [dbGet $out_net.instTerms] {lappend out_terms [dbGet $it.name]}
        foreach pin $original_inputs {
            lassign $pin object original_name cell_name
            # Antenna diodes and delay cells are protection inserted by the
            # tools; a split that also relays one of them is still a correct
            # buffered branch, so it is reported rather than rejected.
            set ordinary [expr {![string match ANTENNA* $cell_name] && ![string match DEL* $cell_name]}]
            set moved [expr {$original_name in $out_terms}]
            set kept  [expr {$original_name in $in_terms}]
            set chosen [expr {$original_name in $selected}]
            if {!$moved && !$kept} {error "Fanout ECO dropped a sink: $original_name ($cell_name)"}
            if {$moved && !$chosen} {
                if {$ordinary} {
                    error "Fanout ECO moved an unselected sink: $original_name ($cell_name)"
                } else {
                    puts "EDA_FANOUT_NOTE net=$net_name relayed $cell_name pin=$original_name"
                }
            }
            if {!$moved && $chosen} {error "Fanout ECO left a selected sink behind: $original_name ($cell_name)"}
        }
        puts "EDA_FANOUT_SPLIT net=$net_name driver=$driver_name old_load=$actual limit=$maximum moved=[llength $selected] original_inputs=[llength $original_inputs] buffer=$new_instance new_net=$output_net_now"
    }
    eda_eval 32_eco_legalize {globalNetConnect VDD -type pgpin -pin VDD -all; globalNetConnect VSS -type pgpin -pin VSS -all; refinePlace}
    eda_eval 32_eco_route {ecoRoute}
    eda_eval 32_eco_reset {setEcoMode -reset}
    eda_eval 32_eco_extract {extractRC}
    eda_eval 32_eco_setup {timeDesign -postRoute -expandedViews -outDir ../my_soc_top/reports/postRoute_fanout_check}
    eda_eval 32_eco_hold {timeDesign -postRoute -hold -expandedViews -outDir ../my_soc_top/reports/postRoute_fanout_check}
    return [llength $eda_fanout_targets]
}
