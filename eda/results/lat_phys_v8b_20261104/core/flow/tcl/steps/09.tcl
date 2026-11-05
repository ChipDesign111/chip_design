addInst -cell PVSS1CDG -inst i_pad_N_vss_1 -loc {600 1685.4} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS1CDG -inst i_pad_S_vss_1 -loc {600 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS1CDG -inst i_pad_W_vss_1 -loc {0 600} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS1CDG -inst i_pad_E_vss_1 -loc {1685.4 600} -ori R90 -place_status fixed -dontSnapToPlacementGrid
foreach pi [dbGet top.insts.name i_pad_?_vss_1 -p] {puts "FIRST_POWER_PAD [dbGet $pi.name] [dbGet $pi.orient] [dbGet $pi.box]"}

addInst -cell PVSS1CDG -inst i_pad_N_vss_2 -loc {700 1685.4} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS2CDG -inst i_pad_N_vssio -loc {800 1685.4} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD1CDG -inst i_pad_N_vdd_1 -loc {900 1685.4} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD1CDG -inst i_pad_N_vdd_2 -loc {1000 1685.4} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD2CDG -inst i_pad_N_vddio -loc {1100 1685.4} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD2POC -inst i_pad_N_poc -loc {1200 1685.4} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS1CDG -inst i_pad_S_vss_2 -loc {700 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS2CDG -inst i_pad_S_vssio -loc {800 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD1CDG -inst i_pad_S_vdd_1 -loc {900 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD1CDG -inst i_pad_S_vdd_2 -loc {1000 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD2CDG -inst i_pad_S_vddio -loc {1100 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD2POC -inst i_pad_S_poc -loc {1200 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS1CDG -inst i_pad_W_vss_2 -loc {0 700} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS2CDG -inst i_pad_W_vssio -loc {0 800} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD1CDG -inst i_pad_W_vdd_1 -loc {0 900} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD1CDG -inst i_pad_W_vdd_2 -loc {0 1000} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD2CDG -inst i_pad_W_vddio -loc {0 1100} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD2POC -inst i_pad_W_poc -loc {0 1200} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS1CDG -inst i_pad_E_vss_2 -loc {1685.4 700} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVSS2CDG -inst i_pad_E_vssio -loc {1685.4 800} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD1CDG -inst i_pad_E_vdd_1 -loc {1685.4 900} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD1CDG -inst i_pad_E_vdd_2 -loc {1685.4 1000} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD2CDG -inst i_pad_E_vddio -loc {1685.4 1100} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PVDD2POC -inst i_pad_E_poc -loc {1685.4 1200} -ori R90 -place_status fixed -dontSnapToPlacementGrid
puts "POWER_PAD_COUNT [llength [dbGet -e top.insts.name i_pad_?_*]]"
saveIoFile -locations -includeCellName ../my_soc_top/my_soc_top_io_beforeFiller.io

saveDesign ../my_soc_top/backup/my_soc_top_preIORegistration.enc
set io_die [lindex [dbGet top.fPlan.box] 0]
lassign $io_die io_dx0 io_dy0 io_dx1 io_dy1
set io_tol 0.001
set io_rows [dict create top {} bottom {} left {} right {}]
set io_corners [dict create]
set io_before [dict create]
foreach io_inst [dbGet top.insts] {
    set io_class [dbGet $io_inst.cell.baseClass]
    if {$io_class ni {pad corner}} {continue}
    set io_subclass [dbGet $io_inst.cell.subClass]
    if {[string match -nocase *spacer* $io_subclass]} {continue}
    set io_name [dbGet $io_inst.name]
    set io_cell [dbGet $io_inst.cell.name]
    if {[regexp {["\\]} "$io_name$io_cell"]} {
        error "Unsupported quote/backslash in IO name or master: $io_name"
    }
    if {[dbGet $io_inst.pStatus] ne "fixed"} {
        error "IO must be fixed before registration: $io_name"
    }
    set io_box [lindex [dbGet $io_inst.box] 0]
    lassign $io_box io_x0 io_y0 io_x1 io_y1
    set io_ori [dbGet $io_inst.orient]
    if {$io_x0 < $io_dx0-$io_tol || $io_y0 < $io_dy0-$io_tol ||
        $io_x1 > $io_dx1+$io_tol || $io_y1 > $io_dy1+$io_tol} {
        error "IO outside measured Die: $io_name"
    }
    dict set io_before $io_name [list $io_box $io_ori]
    if {$io_class eq "corner"} {
        set io_horizontal ""
        set io_vertical ""
        if {abs($io_x0-$io_dx0) < $io_tol} {set io_horizontal left}
        if {abs($io_x1-$io_dx1) < $io_tol} {set io_horizontal right}
        if {abs($io_y0-$io_dy0) < $io_tol} {set io_vertical bottom}
        if {abs($io_y1-$io_dy1) < $io_tol} {set io_vertical top}
        if {$io_horizontal eq "" || $io_vertical eq ""} {
            error "Corner does not touch a rectangle corner: $io_name"
        }
        set io_side "$io_vertical$io_horizontal"
        if {[dict exists $io_corners $io_side]} {
            error "Duplicate corner side: $io_side"
        }
        dict set io_corners $io_side [list $io_name $io_cell $io_ori]
    } else {
        set io_distances [list \
            [list [expr {abs($io_y0-$io_dy0)}] bottom] \
            [list [expr {abs($io_dy1-$io_y1)}] top] \
            [list [expr {abs($io_x0-$io_dx0)}] left] \
            [list [expr {abs($io_dx1-$io_x1)}] right]]
        set io_distances [lsort -real -index 0 $io_distances]
        set io_indent [lindex $io_distances 0 0]
        if {[lindex $io_distances 1 0]-$io_indent < $io_tol} {
            error "IO side is ambiguous from physical box: $io_name"
        }
        set io_side [lindex $io_distances 0 1]
        if {$io_side in {top bottom}} {
            set io_offset [expr {$io_x0-$io_dx0}]
        } else {
            set io_offset [expr {$io_y0-$io_dy0}]
        }
        dict lappend io_rows $io_side [list $io_offset $io_name $io_cell $io_indent $io_ori]
    }
}
if {[dict size $io_corners] != 4} {
    error "Expected exactly four corners in this perimeter"
}
set io_count 0
foreach io_side {top bottom left right} {
    set io_side_count [llength [dict get $io_rows $io_side]]
    incr io_count $io_side_count
    puts "$io_side : $io_side_count PAD"
}
if {$io_count == 0} {error "No CLASS PAD instances; check native LEF"}
set io_tmp_path ../my_soc_top/io_registration_tmp.io
set io_fd [open $io_tmp_path w]
puts $io_fd "(globals\n version = 3\n io_order = default\n)\n(iopad"
foreach io_side {topright top topleft left bottomleft bottom bottomright right} {
    puts $io_fd " ($io_side"
    if {[dict exists $io_corners $io_side]} {
        lassign [dict get $io_corners $io_side] io_name io_cell io_ori
        puts $io_fd [format {  (inst name="%s" cell="%s" orientation=%s place_status=fixed)} $io_name $io_cell $io_ori]
    } else {
        foreach io_row [lsort -real -index 0 [dict get $io_rows $io_side]] {
            lassign $io_row io_offset io_name io_cell io_indent io_ori
            puts $io_fd [format {  (inst name="%s" cell="%s" offset=%.6f indent=%.6f orientation=%s place_status=fixed)} $io_name $io_cell $io_offset $io_indent $io_ori]
        }
    }
    puts $io_fd " )"
}
puts $io_fd ")"
close $io_fd

loadIoFile $io_tmp_path -noAdjustDieSize -specifiedIosOnly
foreach io_name [dict keys $io_before] {
    set io_inst [dbGet top.insts.name $io_name -p]
    lassign [dict get $io_before $io_name] io_old_box io_old_ori
    set io_new_box [lindex [dbGet $io_inst.box] 0]
    foreach io_old_value $io_old_box io_new_value $io_new_box {
        if {abs($io_old_value-$io_new_value) > $io_tol} {
            error "IO moved during side registration: $io_name"
        }
    }
    if {[dbGet $io_inst.orient] ne $io_old_ori} {
        error "IO orientation changed during side registration: $io_name"
    }
}
file delete $io_tmp_path
saveIoFile -locations -includeCellName ../my_soc_top/my_soc_top_io_registered.io
defOut ../my_soc_top/my_soc_top_io_registered.def

dbGet top.fPlan.box
