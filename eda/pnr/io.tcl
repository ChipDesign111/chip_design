# Dynamic rectangular single-ring IO insertion; source after floorplan.tcl.
# Physical bond cells intentionally overlap their corresponding PADs.
pnr4::assert {[info exists pnr4::die]} "Source floorplan.tcl first"
lassign $pnr4::die dx0 dy0 dx1 dy1
lassign [pnr4::size PCORNER] corner_width corner_height
lassign [pnr4::size PDDW0204CDG] pad_width pad_depth
lassign [pnr4::size PAD60LU_OBV] bond_width bond_depth
pnr4::assert {abs($corner_width-$pad_depth)<$pnr4::tol && abs($corner_height-$pad_depth)<$pnr4::tol} "Unsupported corner/PAD geometry"
set pnr4::pad_depth $pad_depth
set pnr4::tie_exclude_file [file join $output_root reports io_supply_tie_exclude.txt]
set pnr4::io_supply_pads [dict create]

# Capture every actual top-level load/driver before touching any functional net.
foreach port {clk_i rst_ni tck_i tms_i td_i td_o} {
    set term [pnr4::one [dbGet top.terms.name $port -p] "top port $port"]
    set external [dbGet $term.net.name]
    set original [pnr4::term_pairs [pnr4::net $external]]
    pnr4::assert {[llength $original]>0} "Port $port has no original core endpoint"
    dict set pnr4::signal_map $port [dict create ext_net $external core_net __asic_core_${port} core_terms $original]
}
foreach {name x y orientation} [list \
    i_corner_SW $dx0 $dy0 R0 \
    i_corner_SE [expr {$dx1-$corner_width}] $dy0 MY \
    i_corner_NW $dx0 [expr {$dy1-$corner_height}] MX \
    i_corner_NE [expr {$dx1-$corner_width}] [expr {$dy1-$corner_height}] R180] {
    addInst -physical -cell PCORNER -inst $name -loc [list $x $y] -ori $orientation -place_status fixed -dontSnapToPlacementGrid
    lappend pnr4::io_corners $name
}
set supply_specs {
    {vss_1 PVSS1CDG VSS} {vss_2 PVSS1CDG VSS}
    {vssio PVSS2CDG VSSPST} {vdd_1 PVDD1CDG VDD}
    {vdd_2 PVDD1CDG VDD} {vddio PVDD2CDG VDDPST}
    {poc PVDD2POC VDDPST}
}
set rows [dict create N [concat [list {signal clk_i}] $supply_specs [list {signal rst_ni}]] \
    S [concat [list {signal tck_i} {signal tms_i}] $supply_specs [list {signal td_i} {signal td_o}]] \
    W $supply_specs E $supply_specs]
foreach side {N S W E} {
    set specifications [dict get $rows $side]
    set span [expr {$side in {N S} ? $dx1-$dx0 : $dy1-$dy0}]
    set usable [expr {$span-2*$pad_depth}]
    set gap [expr {($usable-[llength $specifications]*$pad_width)/([llength $specifications]+1)}]
    pnr4::assert {$gap > 20.0} "Insufficient IO spacing on side $side"
    set ordinal 0
    foreach specification $specifications {
        incr ordinal
        set along [pnr4::grid [expr {$pad_depth+$ordinal*$gap+($ordinal-1)*$pad_width}]]
        switch $side {
            N {set x [expr {$dx0+$along}]; set y [expr {$dy1-$pad_depth}]; set orientation R180}
            S {set x [expr {$dx0+$along}]; set y $dy0; set orientation R0}
            W {set x $dx0; set y [expr {$dy0+$along}]; set orientation R270}
            E {set x [expr {$dx1-$pad_depth}]; set y [expr {$dy0+$along}]; set orientation R90}
        }
        if {[lindex $specification 0] eq "signal"} {
            set port [lindex $specification 1]
            set pad i_pad_${port}
            set master PDDW0204CDG
        } else {
            lassign $specification suffix master supply
            set pad i_pad_${side}_${suffix}
            dict set pnr4::io_supply_pads $side $suffix $pad
        }
        lassign [pnr4::size $master] width depth
        pnr4::assert {abs($width-$pad_width)<$pnr4::tol && abs($depth-$pad_depth)<$pnr4::tol} "Unexpected PAD size: $master"
        addInst -cell $master -inst $pad -loc [list $x $y] -ori $orientation -place_status fixed -dontSnapToPlacementGrid
        lappend pnr4::io_pads $pad
        if {[lindex $specification 0] eq "signal"} {
            set record [dict get $pnr4::signal_map $port]
            set core_net [dict get $record core_net]
            pnr4::assert {[dbGet top.nets.name $core_net] eq {0x0}} "Core net already exists: $core_net"
            addNet $core_net
            foreach endpoint [dict get $record core_terms] {
                lassign $endpoint instance pin
                detachTerm $instance $pin
                attachTerm $instance $pin $core_net
            }
            attachTerm $pad PAD [dict get $record ext_net]
            if {$port eq "td_o"} {
                attachTerm $pad I $core_net
                foreach pin {OEN IE PE DS} {attachTerm $pad $pin 1'b0}
                dict set record core_pad_pin I
            } else {
                attachTerm $pad C $core_net
                foreach pin {OEN IE} {attachTerm $pad $pin 1'b1}
                foreach pin {PE DS I} {attachTerm $pad $pin 1'b0}
                dict set record core_pad_pin C
            }
            dict set record pad $pad
            dict set pnr4::signal_map $port $record
        }
        # The bond placement comes from this PAD's measured box and the
        # loaded bond master dimensions, never from the CPU template's die.
        lassign [pnr4::box [pnr4::inst $pad]] px0 py0 px1 py1
        switch $side {
            N {set bx $px0; set by [expr {$dy1-$bond_depth}]}
            S {set bx $px0; set by $dy0}
            W {set bx $dx0; set by $py0}
            E {set bx [expr {$dx1-$bond_depth}]; set by $py0}
        }
        set bond i_bond_[string range $pad 6 end]
        addInst -physical -cell PAD60LU_OBV -inst $bond -loc [list $bx $by] -ori $orientation -place_status fixed -dontSnapToPlacementGrid
        lappend pnr4::io_bonds $bond
    }
}
pnr4::assert {[llength $pnr4::io_pads]==34 && [llength $pnr4::io_corners]==4 && [llength $pnr4::io_bonds]==34} "Wrong IO instance counts"

proc pnr4::assert_signal_connectivity {} {
    variable signal_map
    global output_root
    set report [open [file join $output_root reports io_signal_connectivity.rpt] w]
    dict for {port record} $signal_map {
        set pad [dict get $record pad]
        set core_net [dict get $record core_net]
        set external [dict get $record ext_net]
        set expected [lsort [concat [dict get $record core_terms] [list [list $pad [dict get $record core_pad_pin]]]]]
        pnr4::assert {[pnr4::term_pairs [pnr4::net $core_net]] eq $expected} "Changed/lost original core endpoint for $port"
        pnr4::assert {[pnr4::term_pairs [pnr4::net $external]] eq [list [list $pad PAD]]} "External net of $port bypasses its PAD"
        set term [pnr4::one [dbGet top.terms.name $port -p] "top port $port"]
        pnr4::assert {[dbGet $term.net.name] eq $external} "Top port net changed for $port"
        puts $report "PASS port=$port pad=$pad external=$external core=$core_net original_core_endpoints=[llength [dict get $record core_terms]]"
        puts $report "CORE_ENDPOINTS [dict get $record core_terms]"
    }
    close $report
}
pnr4::assert_signal_connectivity

# Register fixed PADs from actual bounding boxes, checking that loadIoFile
# preserves every position/orientation. Bond cells are not IO-site members.
set registered [dict create top {} bottom {} left {} right {}]
set corners [dict create]
set before [dict create]
foreach name [concat $pnr4::io_pads $pnr4::io_corners] {
    set pointer [pnr4::inst $name]
    set box [pnr4::box $pointer]
    pnr4::inside $box $pnr4::die "IO $name"
    set orientation [dbGet $pointer.orient]
    dict set before $name [list $box $orientation]
    lassign $box x0 y0 x1 y1
    if {$name in $pnr4::io_corners} {
        set horizontal [expr {abs($x0-$dx0)<$pnr4::tol ? "left" : "right"}]
        set vertical [expr {abs($y0-$dy0)<$pnr4::tol ? "bottom" : "top"}]
        dict set corners ${vertical}${horizontal} [list $name PCORNER $orientation]
    } else {
        set distances [lsort -real -index 0 [list [list [expr {abs($y0-$dy0)}] bottom] [list [expr {abs($dy1-$y1)}] top] [list [expr {abs($x0-$dx0)}] left] [list [expr {abs($dx1-$x1)}] right]]]
        lassign [lindex $distances 0] indent edge
        pnr4::assert {$indent<$pnr4::tol} "PAD does not touch the die edge: $name"
        set offset [expr {$edge in {top bottom} ? $x0-$dx0 : $y0-$dy0}]
        dict lappend registered $edge [list $offset $name [dbGet $pointer.cell.name] $indent $orientation]
    }
}
set io_file [file join $output_root outputs io_registration.io]
set handle [open $io_file w]
puts $handle "(globals\n version = 3\n io_order = default\n)\n(iopad"
foreach edge {topright top topleft left bottomleft bottom bottomright right} {
    puts $handle " ($edge"
    if {[dict exists $corners $edge]} {
        lassign [dict get $corners $edge] name master orientation
        puts $handle [format {  (inst name="%s" cell="%s" orientation=%s place_status=fixed)} $name $master $orientation]
    } else {
        foreach entry [lsort -real -index 0 [dict get $registered $edge]] {
            lassign $entry offset name master indent orientation
            puts $handle [format {  (inst name="%s" cell="%s" offset=%.6f indent=%.6f orientation=%s place_status=fixed)} $name $master $offset $indent $orientation]
        }
    }
    puts $handle " )"
}
puts $handle ")"
close $handle
loadIoFile $io_file -noAdjustDieSize -specifiedIosOnly
dict for {name entry} $before {
    lassign $entry old_box old_orientation
    set pointer [pnr4::inst $name]
    foreach old $old_box new [pnr4::box $pointer] {
        pnr4::assert {abs($old-$new)<$pnr4::tol} "IO registration moved $name"
    }
    pnr4::assert {[dbGet $pointer.orient] eq $old_orientation} "IO registration rotated $name"
}
foreach {edge orientation} {top R180 bottom R0 left R270 right R90} {
    addIoFiller -cell {PFILLER20 PFILLER10 PFILLER5 PFILLER1 PFILLER05 PFILLER0005} -prefix IOF_${edge} -side $edge -fillerOrient $orientation
}
proc pnr4::assert_io_geometry {} {
    variable die; variable io_pads; variable io_corners; variable io_bonds
    foreach name [concat $io_pads $io_corners $io_bonds] {
        set pointer [pnr4::inst $name]
        pnr4::inside [pnr4::box $pointer] $die "IO/bond $name"
        pnr4::assert {[dbGet $pointer.pStatus] eq "fixed"} "Unfixed IO/bond $name"
    }
    foreach {name allowed} {i_corner_SW {R0 N} i_corner_SE {MY FN} i_corner_NW {MX FS} i_corner_NE {R180 S}} {
        pnr4::assert {[dbGet [pnr4::inst $name].orient] in $allowed} "Wrong native corner orientation: $name"
    }
}
proc pnr4::assert_io_abutment {} {
    variable die; variable io_pads; variable pad_depth; variable tol
    global output_root
    lassign $die dx0 dy0 dx1 dy1
    set intervals [dict create N {} S {} W {} E {}]
    set names $io_pads
    foreach pointer [dbGet top.insts.name IOF_* -p] {
        if {$pointer ne {0x0}} {lappend names [dbGet $pointer.name]}
    }
    foreach name $names {
        set pointer [pnr4::inst $name]
        set box [pnr4::box $pointer]
        pnr4::inside $box $die "IO ring $name"
        lassign $box x0 y0 x1 y1
        if {abs($y1-$dy1)<$tol} {set side N; set start $x0; set end $x1
        } elseif {abs($y0-$dy0)<$tol} {set side S; set start $x0; set end $x1
        } elseif {abs($x0-$dx0)<$tol} {set side W; set start $y0; set end $y1
        } elseif {abs($x1-$dx1)<$tol} {set side E; set start $y0; set end $y1
        } else {error "IO/filler is not on the die boundary: $name"}
        set allowed [dict get [dict create N {R180 S} S {R0 N} W {R270 E} E {R90 W}] $side]
        pnr4::assert {[dbGet $pointer.orient] in $allowed} "Wrong native IO rail orientation: $name"
        dict lappend intervals $side [list $start $end $name]
    }
    set report [open [file join $output_root reports io_abutment.rpt] w]
    foreach side {N S W E} {
        set last [expr {$side in {N S} ? $dx0+$pad_depth : $dy0+$pad_depth}]
        foreach entry [lsort -real -index 0 [dict get $intervals $side]] {
            lassign $entry start end name
            pnr4::assert {abs($start-$last)<$tol} "Native IO rail gap/overlap before $name: [expr {$start-$last}] um"
            set last $end
        }
        set expected [expr {$side in {N S} ? $dx1-$pad_depth : $dy1-$pad_depth}]
        pnr4::assert {abs($last-$expected)<$tol} "Native IO rail does not reach its corner on $side"
        puts $report "PASS side=$side abutting_pad_and_filler_count=[llength [dict get $intervals $side]] end=$last"
    }
    close $report
}
pnr4::assert_io_geometry
pnr4::assert_io_abutment
pnr4::assert_signal_connectivity
saveIoFile -locations -includeCellName [file join $output_root outputs my_soc_top.io]
saveNetlist [file join $output_root outputs my_soc_top_post_io.v] -phys
defOut [file join $output_root outputs my_soc_top_post_io.def]
pnr4::checkpoint io
puts "PNR_IO_FINISHED functional=6 supply=28 corner=4 bond=34"
