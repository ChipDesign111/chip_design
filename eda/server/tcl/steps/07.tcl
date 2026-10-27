addInst -cell PDDW0204CDG -inst i_pad_clk -loc {300 1685.4} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PDDW0204CDG -inst i_pad_rst_n -loc {1400 1685.4} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PDDW0204CDG -inst i_pad_tck -loc {250 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PDDW0204CDG -inst i_pad_tms -loc {450 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PDDW0204CDG -inst i_pad_tdi -loc {1400 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -cell PDDW1216CDG -inst i_pad_tdo -loc {1600 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
foreach pi [dbGet top.insts.name i_pad_* -p] {puts "SIGNAL_PAD [dbGet $pi.name] [dbGet $pi.orient] [dbGet $pi.pStatus] [dbGet $pi.box]"}
