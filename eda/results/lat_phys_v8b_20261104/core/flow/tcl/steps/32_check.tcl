timeDesign -postRoute -expandedViews -outDir ../my_soc_top/reports/postRoute_holdAuto_check
timeDesign -postRoute -hold -expandedViews -outDir ../my_soc_top/reports/postRoute_holdAuto_check

globalNetConnect VDD -type pgpin -pin VDD -all
globalNetConnect VSS -type pgpin -pin VSS -all
checkPlace ../my_soc_top/my_soc_top_postHoldAuto_place.rpt -ignoreOutOfCore
verify_drc -check_only default -limit 100000 -report ../my_soc_top/my_soc_top_postHoldAuto_drc.rpt
verifyConnectivity -type regular -error 100000 -report ../my_soc_top/my_soc_top_postHoldAuto_signal.rpt
verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -error 100000 -report ../my_soc_top/my_soc_top_postHoldAuto_pg.rpt
verifyProcessAntenna -report ../my_soc_top/my_soc_top_postHoldAuto_antenna.rpt
saveDesign ../my_soc_top/backup/my_soc_top_postRoute_timingFixed.enc
