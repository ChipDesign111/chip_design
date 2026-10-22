placeInstance i_mainmem/i_mainmem 250 650 R0 -fixed
addHaloToBlock 26 26 26 26 i_mainmem/i_mainmem -snapToSite
dbGet [dbGet top.insts.name i_mainmem/i_mainmem -p].box
dbGet [dbGet top.insts.name i_mainmem/i_mainmem -p].pHaloBox
checkFPlan -reportUtil -outFile ../my_soc_top/my_soc_top_floorplan_check.rpt

set mb [lindex [dbGet [dbGet top.insts.name i_mainmem/i_mainmem -p].box] 0]
set hb [lindex [dbGet [dbGet top.insts.name i_mainmem/i_mainmem -p].pHaloBox] 0]
lassign $mb mx0 my0 mx1 my1
lassign $hb hx0 hy0 hx1 hy1
set hm [list [expr {$mx0-$hx0}] [expr {$my0-$hy0}] [expr {$hx1-$mx1}] [expr {$hy1-$my1}]]
puts "ACTUAL_HALO_MARGINS $hm"
foreach m $hm {if {$m<20.0} {error "SRAM halo is less than 20 um"}}
saveDesign ../my_soc_top/backup/my_soc_top_postMacroPlace.enc
