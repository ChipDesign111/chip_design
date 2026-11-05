# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
placeInstance i_mainmem/i_sram/i_macro 250.000000 650.000000 R0 -fixed
addHaloToBlock 26 26 26 26 i_mainmem/i_sram/i_macro -snapToSite
dbGet [dbGet top.insts.name i_mainmem/i_sram/i_macro -p].box
dbGet [dbGet top.insts.name i_mainmem/i_sram/i_macro -p].pHaloBox
checkFPlan -reportUtil -outFile ../my_soc_top/my_soc_top_floorplan_check.rpt

set mb [lindex [dbGet [dbGet top.insts.name i_mainmem/i_sram/i_macro -p].box] 0]
set hb [lindex [dbGet [dbGet top.insts.name i_mainmem/i_sram/i_macro -p].pHaloBox] 0]
lassign $mb mx0 my0 mx1 my1
lassign $hb hx0 hy0 hx1 hy1
set hm [list [expr {$mx0-$hx0}] [expr {$my0-$hy0}] [expr {$hx1-$mx1}] [expr {$hy1-$my1}]]
puts "ACTUAL_HALO_MARGINS $hm"
foreach m $hm {if {$m<20.0} {error "SRAM halo is less than 20 um"}}
saveDesign ../my_soc_top/backup/my_soc_top_postMacroPlace.enc

