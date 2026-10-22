# Idempotent helpers: safe to reload after restoring checkpoint context.
namespace eval pnr4 {
    variable tol 0.002
    variable die
    variable core
    variable macro_box
    variable macro_halo
    variable signal_map
    if {![info exists signal_map]} {set signal_map [dict create]}
    variable supply_terms
    if {![info exists supply_terms]} {set supply_terms {}}
    variable io_pads
    if {![info exists io_pads]} {set io_pads {}}
    variable io_corners
    if {![info exists io_corners]} {set io_corners {}}
    variable io_bonds
    if {![info exists io_bonds]} {set io_bonds {}}
}
proc pnr4::assert {condition message} {
    if {![uplevel 1 [list expr $condition]]} {error $message}
}
proc pnr4::one {values description} {
    if {$values eq {0x0} || [llength $values] != 1} {
        error "Expected one $description; got $values"
    }
    return [lindex $values 0]
}
proc pnr4::inst {name} {
    return [pnr4::one [dbGet top.insts.name $name -p] "instance $name"]
}
proc pnr4::cell {name} {
    return [pnr4::one [dbGet head.libCells.name $name -p] "library cell $name"]
}
proc pnr4::flat_list {value count description} {
    if {[llength $value] == 1} {set value [lindex $value 0]}
    if {[llength $value] != $count} {error "Bad $description: $value"}
    return $value
}
proc pnr4::box {pointer} {
    return [pnr4::flat_list [dbGet $pointer.box] 4 "bounding box"]
}
proc pnr4::size {master} {
    return [pnr4::flat_list [dbGet [pnr4::cell $master].size] 2 "$master size"]
}
proc pnr4::inside {inner outer description} {
    variable tol
    lassign $inner ax ay bx by
    lassign $outer x0 y0 x1 y1
    pnr4::assert {$ax < $bx && $ay < $by && $ax >= $x0-$tol && $ay >= $y0-$tol && $bx <= $x1+$tol && $by <= $y1+$tol} "$description is outside $outer or degenerate: $inner"
}
proc pnr4::grid {coordinate} {
    # Native IO filler resolution is 0.005 um; do not round to a core site.
    return [expr {round($coordinate/0.005)*0.005}]
}
proc pnr4::net {name} {
    return [pnr4::one [dbGet top.nets.name $name -p] "net $name"]
}
proc pnr4::iterm {instance pin} {
    set matches {}
    foreach term [dbGet [pnr4::inst $instance].instTerms] {
        if {$term eq {0x0}} {continue}
        if {[lindex [dbGet $term.cellTerm.name] 0] eq $pin} {lappend matches $term}
    }
    return [pnr4::one $matches "ITerm $instance/$pin"]
}
proc pnr4::term_pairs {net_pointer} {
    set result {}
    foreach term [dbGet $net_pointer.instTerms] {
        if {$term eq {0x0}} {continue}
        # dbGet returns a Tcl list even for a single name. Unwrap it so bus
        # instance names such as foo_reg[0] do not retain literal list braces.
        lappend result [list [lindex [dbGet $term.inst.name] 0] [lindex [dbGet $term.cellTerm.name] 0]]
    }
    return [lsort $result]
}
proc pnr4::checkpoint {stage} {
    global output_root
    saveDesign [file join $output_root backup my_soc_top_${stage}.enc]
}
