setPlaceMode -place_detail_preroute_as_obs {} -place_detail_use_check_drc true
setPlaceMode -place_global_ignore_scan true -place_global_reorder_scan false
place_opt_design
checkPlace ../my_soc_top/my_soc_top_place_check.rpt -ignoreOutOfCore

saveDesign ../my_soc_top/backup/my_soc_top_postPlace.enc
