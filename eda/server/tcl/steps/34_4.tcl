rcOut -view func_tt_io -cUnit pF -spef ../my_soc_top/outputs/manual_final/my_soc_top_tt_io.spef.gz
write_sdf -min_view func_tt_io -typ_view func_tt_io -max_view func_tt_io -recompute_delay_calc ../my_soc_top/outputs/manual_final/my_soc_top_tt_io.sdf.gz
if {[info exists eda_enable_pvt] && $eda_enable_pvt} {
    write_sdf -min_view func_ffm40_io -typ_view func_tt_io -max_view func_ss_io -recompute_delay_calc ../my_soc_top/outputs/manual_final/my_soc_top_pvt.sdf.gz
}
