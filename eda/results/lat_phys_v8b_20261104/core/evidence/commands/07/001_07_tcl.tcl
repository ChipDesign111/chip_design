# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
addInst -cell PDDW0204CDG -inst i_pad_clk -loc {300.000000 1833.240000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PDDW0204CDG -inst i_pad_rst_n -loc {1400.000000 1833.240000} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PDDW0204CDG -inst i_pad_tck -loc {250.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PDDW0204CDG -inst i_pad_tms -loc {450.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PDDW0204CDG -inst i_pad_tdi -loc {1400.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PDDW0204CDG -inst i_pad_tdo -loc {1600.000000 0.000000} -ori R0 -place_status fixed -dontSnapToPlacementGrid
if {[llength [dbGet -e top.insts.cell.name PDDW0204CDG -p2]] != 6} {error "Signal PAD count mismatch"}

