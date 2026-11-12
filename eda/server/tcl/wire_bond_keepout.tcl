# Encode the native C18 WB CB.S.2.M5/M6 2.5um clearance before routing.
# Applies to regular signal routes only. Original PG connections are preserved.
proc eda_apply_wire_bond_keepouts {} {
    set pads [dbGet -e top.insts.cell.name PAD60LU_OBV -p2]
    if {[llength $pads] != 34} {error "Wire Bond keepout: expected 34 native PADs"}
    foreach pad $pads {
        set inst [dbGet ${pad}.name]
        set name WB_SIGNAL_${inst}
        if {[llength [dbGet -e top.fPlan.rBlkgs.name $name -p]] != 0} {
            error "Wire Bond keepout already exists: $name"
        }
        set box [lindex [dbGet ${pad}.box] 0]
        createRouteBlk -name $name -box $box -layer {METAL5 METAL6} -exceptpgnet -spacing 2.5
        puts "EDA_WB_SIGNAL_KEEPOUT $inst BOX=[dbGet ${pad}.box] LAYERS=METAL5,METAL6 SPACING_UM=2.5 EXCEPT_PG=1"
    }
    puts "EDA_WB_SIGNAL_KEEPOUT_COUNT 34"
    eda_check_wire_bond_keepouts
}

proc eda_check_wire_bond_keepouts {} {
    set pads [dbGet -e top.insts.cell.name PAD60LU_OBV -p2]
    if {[llength $pads] != 34} {error "Wire Bond keepout: PAD identity mismatch"}
    foreach pad $pads {
        set inst [dbGet ${pad}.name]
        set blocks [dbGet -e top.fPlan.rBlkgs.name WB_SIGNAL_${inst} -p]
        # Native 21.16 creates one object for each selected routing layer.
        if {[llength $blocks] != 2} {error "Wire Bond keepout objects missing: $inst"}
        set layers {}
        foreach block $blocks {
            lappend layers [dbGet ${block}.layer.name]
            if {[dbGet ${block}.isExceptPGNet] != 1 || [dbGet ${block}.isPGNetOnly] != 0 || abs([dbGet ${block}.spacing]-2.5)>0.000001} {
                error "Wire Bond keepout properties changed: $inst"
            }
        }
        if {[lsort $layers] ne {METAL5 METAL6}} {error "Wire Bond keepout layers changed: $inst"}
    }
    puts "EDA_WB_SIGNAL_KEEPOUT_READBACK 34_PADS_68_LAYER_OBJECTS_SPACING_2.5_EXCEPT_PG"
}
