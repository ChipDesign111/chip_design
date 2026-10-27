set tie_supply_tmp [open ../my_soc_top/tie_supply_exclude_tmp.txt w]
puts $tie_supply_tmp [join {
i_pad_N_vddio/VDDPST
i_pad_N_poc/VDDPST
i_pad_N_vssio/VSSPST
i_pad_S_vddio/VDDPST
i_pad_S_poc/VDDPST
i_pad_S_vssio/VSSPST
i_pad_W_vddio/VDDPST
i_pad_W_poc/VDDPST
i_pad_W_vssio/VSSPST
i_pad_E_vddio/VDDPST
i_pad_E_poc/VDDPST
i_pad_E_vssio/VSSPST
} "\n"]
close $tie_supply_tmp

setTieHiLoMode -cell {TIEHBWP7T TIELBWP7T} -maxFanout 1 -maxDistance 100
addTieHiLo -cellPin {PDDW0204CDG:I PDDW0204CDG:DS PDDW0204CDG:OEN PDDW0204CDG:PE PDDW0204CDG:IE PDDW1216CDG:DS PDDW1216CDG:OEN PDDW1216CDG:PE PDDW1216CDG:IE}
setTieHiLoMode -cell {TIEHBWP7T TIELBWP7T} -maxFanout 8 -maxDistance 50
addTieHiLo -keepExisting true -excludePin ../my_soc_top/tie_supply_exclude_tmp.txt
file delete ../my_soc_top/tie_supply_exclude_tmp.txt
globalNetConnect VDD -type pgpin -pin VDD -all
globalNetConnect VSS -type pgpin -pin VSS -all
refinePlace
checkPlace ../my_soc_top/my_soc_top_postTie_place.rpt -ignoreOutOfCore

saveNetlist ../my_soc_top/my_soc_top_postTie.v -phys
