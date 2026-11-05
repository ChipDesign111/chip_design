# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
addInst -physical -cell PCORNER -inst corner_bottom_left -loc {0.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PCORNER -inst corner_bottom_right -loc {1833.240000 0.000000} -ori MY -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PCORNER -inst corner_top_left -loc {0.000000 1833.240000} -ori MX -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PCORNER -inst corner_top_right -loc {1833.240000 1833.240000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
if {[dbGet [dbGet top.insts.name corner_bottom_left -p].pStatus] ne "fixed" || [dbGet [dbGet top.insts.name corner_bottom_left -p].orient] ne "R0"} {error "Corner placement failed"}
if {[dbGet [dbGet top.insts.name corner_bottom_right -p].pStatus] ne "fixed" || [dbGet [dbGet top.insts.name corner_bottom_right -p].orient] ne "MY"} {error "Corner placement failed"}
if {[dbGet [dbGet top.insts.name corner_top_left -p].pStatus] ne "fixed" || [dbGet [dbGet top.insts.name corner_top_left -p].orient] ne "MX"} {error "Corner placement failed"}
if {[dbGet [dbGet top.insts.name corner_top_right -p].pStatus] ne "fixed" || [dbGet [dbGet top.insts.name corner_top_right -p].orient] ne "R180"} {error "Corner placement failed"}

