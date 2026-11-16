# Native PV* IO masters contain >10um-wide M2 rails. Calibre M2.S.2
# requires 0.6um spacing to unconnected signal metal. The supplied LEF
# obstruction alone allowed 0.45um via-enclosure gaps in aca6c09.
# Keep regular signals out of each power-IO footprint, with 0.65um margin;
# PG routing is exempt so native power connections remain routable.
proc eda_apply_io_m2_keepouts {} {
    set count 0
    foreach pad [dbGet -e top.insts.name i_pad_* -p] {
        set master [dbGet ${pad}.cell.name]
        if {![string match PV* $master]} {continue}
        set inst [dbGet ${pad}.name]
        set name IO_M2_SIGNAL_${inst}
        if {[llength [dbGet -e top.fPlan.rBlkgs.name $name -p]] != 0} {error "Duplicate IO M2 keepout: $name"}
        set box [lindex [dbGet ${pad}.box] 0]
        createRouteBlk -name $name -box $box -layer METAL2 -exceptpgnet -spacing 0.65
        incr count
        puts "EDA_IO_M2_SIGNAL_KEEPOUT $inst MASTER=$master BOX=$box SPACING_UM=0.65 EXCEPT_PG=1"
    }
    if {$count != 28} {error "Expected 28 native power IO M2 keepouts, got $count"}
    eda_check_io_m2_keepouts
}
proc eda_check_io_m2_keepouts {} {
    set count 0
    foreach pad [dbGet -e top.insts.name i_pad_* -p] {
        if {![string match PV* [dbGet ${pad}.cell.name]]} {continue}
        set inst [dbGet ${pad}.name]
        set blocks [dbGet -e top.fPlan.rBlkgs.name IO_M2_SIGNAL_${inst} -p]
        if {[llength $blocks] != 1} {error "Missing IO M2 keepout: $inst"}
        set block [lindex $blocks 0]
        if {[dbGet ${block}.layer.name] ne "METAL2" || [dbGet ${block}.isExceptPGNet] != 1 || [dbGet ${block}.isPGNetOnly] != 0 || abs([dbGet ${block}.spacing]-0.65)>0.000001} {
            error "Changed IO M2 keepout: $inst"
        }
        incr count
    }
    if {$count != 28} {error "Power IO keepout identity changed"}
    puts "EDA_IO_M2_SIGNAL_KEEPOUT_READBACK 28_POWER_PADS_METAL2_SPACING_0.65_EXCEPT_PG"
}
