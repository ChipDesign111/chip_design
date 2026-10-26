# Report-driven, non-inverting buffer split for ordinary single-driver nets.
# Innovus 21.16 disables automatic fanout fixing in optDesign -postRoute.
# Source syntax: installed innovusTCR/ecoAddRepeater.html and setEcoMode.html.
proc eda_literal_net_pattern {name} {
    regsub -all {[][\\.^$*+?(){}|]} $name {\\&} escaped
    return "^${escaped}$"
}
proc eda_db_scalar {path} {
    # dbGet returns a Tcl list even for one string. A bus name is serialized
    # with braces; comparing that list string to a literal name is incorrect.
    set values [dbGet -e $path]
    if {[llength $values] != 1} {error "Expected one database value: $path"}
    return [lindex $values 0]
}
proc eda_eco_terms {terms} {
    # This legacy -term parser splits a space-separated string; it does not
    # remove Tcl list braces around bus pin names. Do not eval the names.
    if {[llength $terms] == 0} {error "Empty ECO terminal selection"}
    foreach term $terms {
        if {$term eq "" || [regexp {[\s{}]} $term]} {error "Unsupported ECO terminal name: $term"}
    }
    return [join $terms " "]
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
        if {[llength $net] != 1 || $net in {{} 0x0} || [eda_db_scalar $net.name] ne $net_name} {error "Fanout net not uniquely resolved: $net_name"}
        if {[dbGet $net.isPwrOrGnd] || [dbGet $net.isClock] || [dbGet $net.isCTSClock] || [llength [dbGet -e $net.terms]]} {
            error "Refuse automatic ECO on supply/clock/external net: $net_name"
        }
        set receivers {}; set drivers {}; set driver_objects {}; set original_inputs {}
        foreach it [dbGet $net.instTerms] {
            if {[dbGet $it.isInput] && [dbGet $it.isOutput]} {error "Bidirectional fanout pin requires manual adaptation"}
            if {[dbGet $it.isOutput]} {
                lappend drivers [eda_db_scalar $it.name]
                lappend driver_objects $it
            }
            if {[dbGet $it.isInput]} {
                lassign [lindex [dbGet $it.pt] 0] x y
                lappend receivers [list $x $y [eda_db_scalar $it.name] [eda_db_scalar $it.inst.cell.name]]
                lappend original_inputs [list $it [eda_db_scalar $it.name]]
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
        set command [list ecoAddRepeater -term [eda_eco_terms $selected] -cell BUFFD2BWP7T -name $name]
        set result [eda_eval 32_fanout_split $command]
        if {[llength $result] != 3} {error "Expected one non-inverting ECO buffer"}
        lassign $result new_instance input_net output_net
        # The native command may return hierarchy-local aliases/escaped bus
        # names. Check actual database connectivity instead of those strings.
        set output_object {}
        foreach pin $original_inputs {
            lassign $pin object original_name
            if {$original_name in $selected} {set output_object [eda_db_scalar $object.net]; break}
        }
        if {$output_object eq ""} {error "Fanout ECO did not split the selected sinks"}
        set output_drivers {}
        foreach pin [dbGet $output_object.instTerms] {
            if {[dbGet $pin.isOutput]} {lappend output_drivers $pin}
        }
        if {[llength $output_drivers] != 1} {error "Unexpected ECO output drivers"}
        set added [eda_db_scalar [lindex $output_drivers 0].inst]
        if {[eda_db_scalar $added.cell.name] ne "BUFFD2BWP7T"} {error "Unexpected ECO buffer instance"}
        set buffer_inputs {}; set buffer_outputs {}
        foreach pin [dbGet $added.instTerms] {
            if {[dbGet $pin.isInput]} {lappend buffer_inputs $pin}
            if {[dbGet $pin.isOutput]} {lappend buffer_outputs $pin}
        }
        if {[llength $buffer_inputs] != 1 || [llength $buffer_outputs] != 1} {error "Unexpected ECO buffer terminals"}
        set input_object [eda_db_scalar [lindex $buffer_inputs 0].net]
        set output_object [eda_db_scalar [lindex $buffer_outputs 0].net]
        if {$input_object eq $output_object || [eda_db_scalar [lindex $driver_objects 0].net] ne $input_object} {error "Unexpected fanout ECO net split"}
        foreach pin $original_inputs {
            lassign $pin object original_name
            # expr would normalize a hexadecimal DB pointer to decimal text.
            if {$original_name in $selected} {set expected $output_object} else {set expected $input_object}
            if {[eda_db_scalar $object.net] ne $expected} {error "Fanout ECO changed an unselected sink"}
        }
        puts "EDA_FANOUT_SPLIT net=$net_name driver=$driver_name old_load=$actual limit=$maximum moved=[llength $selected] original_inputs=[llength $original_inputs] buffer=$new_instance new_net=$output_net"
    }
    eda_eval 32_eco_legalize {globalNetConnect VDD -type pgpin -pin VDD -all; globalNetConnect VSS -type pgpin -pin VSS -all; refinePlace}
    eda_eval 32_eco_route {ecoRoute}
    eda_eval 32_eco_reset {setEcoMode -reset}
    eda_eval 32_eco_extract {extractRC}
    eda_eval 32_eco_setup {timeDesign -postRoute -expandedViews -outDir ../my_soc_top/reports/postRoute_fanout_check}
    eda_eval 32_eco_hold {timeDesign -postRoute -hold -expandedViews -outDir ../my_soc_top/reports/postRoute_fanout_check}
    return [llength $eda_fanout_targets]
}
