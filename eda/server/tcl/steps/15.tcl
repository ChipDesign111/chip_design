setDesignMode -bottomRoutingLayer METAL2 -topRoutingLayer METAL6
getDesignMode -bottomRoutingLayer
getDesignMode -topRoutingLayer
deselectAll
setAddRingMode -reset
setAddRingMode -avoid_short true -stacked_via_bottom_layer METAL1 -stacked_via_top_layer METAL5
addRing -nets {VDD VSS} -type core_rings -follow core -layer {top METAL5 bottom METAL5 left METAL4 right METAL4} -width 10 -spacing 2 -offset 5 -center 0
selectInst i_mainmem/i_mainmem
addRing -nets {VDD VSS} -type block_rings -around selected -layer {top METAL5 bottom METAL5 left METAL4 right METAL4} -width 4 -spacing 2 -offset 10 -center 0
deselectAll
verify_drc -check_only special -report ../my_soc_top/my_soc_top_pg_drc.rpt
