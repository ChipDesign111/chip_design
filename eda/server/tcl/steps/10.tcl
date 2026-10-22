addInst -physical -cell PAD60LU_OBV -inst i_bond_clk -loc {300 1727.24} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_rst_n -loc {1400 1727.24} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_tck -loc {250 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_tms -loc {450 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_tdi -loc {1400 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_tdo -loc {1600 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid

addInst -physical -cell PAD60LU_OBV -inst i_bond_N_vss_1 -loc {600 1727.24} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_N_vss_2 -loc {700 1727.24} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_N_vssio -loc {800 1727.24} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_N_vdd_1 -loc {900 1727.24} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_N_vdd_2 -loc {1000 1727.24} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_N_vddio -loc {1100 1727.24} -ori R180 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_N_poc -loc {1200 1727.24} -ori R180 -place_status fixed -dontSnapToPlacementGrid

addInst -physical -cell PAD60LU_OBV -inst i_bond_S_vss_1 -loc {600 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_S_vss_2 -loc {700 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_S_vssio -loc {800 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_S_vdd_1 -loc {900 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_S_vdd_2 -loc {1000 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_S_vddio -loc {1100 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_S_poc -loc {1200 0} -ori R0 -place_status fixed -dontSnapToPlacementGrid

addInst -physical -cell PAD60LU_OBV -inst i_bond_W_vss_1 -loc {0 600} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_W_vss_2 -loc {0 700} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_W_vssio -loc {0 800} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_W_vdd_1 -loc {0 900} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_W_vdd_2 -loc {0 1000} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_W_vddio -loc {0 1100} -ori R270 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_W_poc -loc {0 1200} -ori R270 -place_status fixed -dontSnapToPlacementGrid

addInst -physical -cell PAD60LU_OBV -inst i_bond_E_vss_1 -loc {1727.24 600} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_E_vss_2 -loc {1727.24 700} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_E_vssio -loc {1727.24 800} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_E_vdd_1 -loc {1727.24 900} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_E_vdd_2 -loc {1727.24 1000} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_E_vddio -loc {1727.24 1100} -ori R90 -place_status fixed -dontSnapToPlacementGrid
addInst -physical -cell PAD60LU_OBV -inst i_bond_E_poc -loc {1727.24 1200} -ori R90 -place_status fixed -dontSnapToPlacementGrid

defOut ../my_soc_top/my_soc_top_preIOFiller.def

puts "BOND_COUNT [llength [dbGet -e top.insts.cell.name PAD60LU_OBV -p2]]"
