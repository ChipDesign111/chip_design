timeDesign -postCTS -expandedViews -outDir ../my_soc_top/reports/postCTS_holdFix_check
timeDesign -postCTS -hold -expandedViews -outDir ../my_soc_top/reports/postCTS_holdFix_check
globalNetConnect VDD -type pgpin -pin VDD -all
globalNetConnect VSS -type pgpin -pin VSS -all
checkPlace ../my_soc_top/my_soc_top_postHoldFix_place.rpt -ignoreOutOfCore
verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -error 100000 -report ../my_soc_top/my_soc_top_postHoldFix_pg.rpt
saveDesign ../my_soc_top/backup/my_soc_top_postCTS_holdResidual.enc
