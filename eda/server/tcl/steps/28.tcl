saveDesign ../my_soc_top/backup/my_soc_top_preCTS.enc
eda_native_opt ccopt_design
saveDesign ../my_soc_top/backup/my_soc_top_postCTS_raw.enc
set_interactive_constraint_modes [all_constraint_modes -active]
set_global timing_io_use_clock_network_latency always
set_propagated_clock [get_clocks {sys_clk jtag_clk}]
set_interactive_constraint_modes {}
globalNetConnect VDD -type pgpin -pin VDD -all
globalNetConnect VSS -type pgpin -pin VSS -all
checkPlace ../my_soc_top/my_soc_top_postCTS_place_check.rpt -ignoreOutOfCore
verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -error 100000 -report ../my_soc_top/my_soc_top_postCTS_pg_connectivity.rpt
timeDesign -postCTS -expandedViews -outDir ../my_soc_top/reports/postCTS
timeDesign -postCTS -hold -expandedViews -outDir ../my_soc_top/reports/postCTS
