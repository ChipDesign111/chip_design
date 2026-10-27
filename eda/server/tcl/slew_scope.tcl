# Physical pin classes: data 0.3ns, internal clock 0.5ns, external PAD 0.6ns.
# Instance constraints are refreshed after topology changes, before reports.
# No library limit is overridden. Newly inserted cells are included at refresh;
# the independent final DRV gate must still report zero Real AND Total violations.
proc eda_apply_slew_scope {} {
    global eda_work step eda_slew_scope_index
    global rm_max_transition rm_max_clock_transition rm_max_pad_transition
    if {![info exists eda_slew_scope_index]} {set eda_slew_scope_index 0}
    incr eda_slew_scope_index
    set pad_names {i_pad_clk/PAD i_pad_rst_n/PAD i_pad_tck/PAD i_pad_tms/PAD i_pad_tdi/PAD i_pad_tdo/PAD}
    set pad_pins [get_pins $pad_names]
    set ports [get_ports {clk_i rst_ni tck_i tms_i td_i td_o}]
    set all_pins [get_pins -leaf -hierarchical *]
    if {[sizeof_collection $pad_pins]!=6 || [sizeof_collection $ports]!=6 || [sizeof_collection $all_pins]<100000} {
        error "Unexpected physical pin/port inventory for slew classes"
    }
    set clock_nets [lsort -unique [concat [dbGet -e top.nets.isClock 1 -p] [dbGet -e top.nets.isCTSClock 1 -p]]]
    set clock_names {}
    foreach net $clock_nets {
        foreach name [dbGet -e $net.instTerms.name] {lappend clock_names $name}
    }
    set clock_names [lsort -unique $clock_names]
    if {[llength $clock_names]>0} {
        set clock_pins [get_pins $clock_names]
        if {[lsort -unique [get_object_name $clock_pins]] ne $clock_names} {
            error "Clock pin lookup was not literal and complete"
        }
    } else {
        # Before the first placement/timing graph, Innovus has not marked
        # clock nets yet. Keep EVERY internal pin at the stricter 0.3ns.
        # Never issue get_pins with an empty pattern (native tool error).
        set clock_pins [remove_from_collection $all_pins $all_pins]
    }
    set clock_pins [remove_from_collection $clock_pins $pad_pins]
    set internal_pins [remove_from_collection $all_pins $pad_pins]
    set data_pins [remove_from_collection $internal_pins $clock_pins]
    set nall [sizeof_collection $all_pins]
    set nd [sizeof_collection $data_pins]
    set nc [sizeof_collection $clock_pins]
    if {($nc<1 && $step>=28) || $nd<100000 || $nall!=$nd+$nc+6} {error "Incomplete or overlapping slew pin classes"}
    set_interactive_constraint_modes [all_constraint_modes -active]
    # A tighter design-wide constraint would also constrain the external PAD.
    # All internal pins receive their stricter class explicitly below. Do not
    # add a clock -data_path 0.3 rule: it also reaches the external TDO port.
    set_max_transition $rm_max_pad_transition [current_design]
    set_max_transition $rm_max_pad_transition [get_clocks {sys_clk jtag_clk}] -clock_path
    set_max_transition $rm_max_pad_transition $ports
    set_max_transition $rm_max_pad_transition $pad_pins
    set_max_transition $rm_max_transition $data_pins
    if {$nc>0} {set_max_transition $rm_max_clock_transition $clock_pins}
    set_interactive_constraint_modes {}
    set folder [file join $eda_work evidence slew_scope]
    file mkdir $folder
    set fd [open [file join $folder [format %02d_%03d.json $step $eda_slew_scope_index]] w]
    puts $fd [format {{"all_leaf_pins":%d,"data_pins":%d,"clock_pins":%d,"external_pad_pins":6,"external_ports":6,"data_limit_ns":%.3f,"clock_limit_ns":%.3f,"pad_limit_ns":%.3f,"library_override":false,"conservative_pre_cts_clock_scope":%s}} $nall $nd $nc $rm_max_transition $rm_max_clock_transition $rm_max_pad_transition [expr {$nc==0 ? "true" : "false"}]]
    close $fd
    puts "EDA_SLEW_SCOPE step=$step all=$nall data=$nd clock=$nc pad=6 ports=6 no_library_override"
}
