globalNetConnect VDD -type pgpin -pin VDD -all
globalNetConnect VSS -type pgpin -pin VSS -all
setFillerMode -core {FILL64BWP7T FILL32BWP7T FILL16BWP7T FILL8BWP7T FILL4BWP7T FILL2BWP7T FILL1BWP7T} -corePrefix FILLER -createRows false -diffCellViol true -ecoMode true -fitGap true -scheme locationFirst -honorPrerouteAsObs false -check_signal_drc true -add_fillers_with_drc false
addFiller
globalNetConnect VDD -type pgpin -pin VDD -all
globalNetConnect VSS -type pgpin -pin VSS -all
checkPlace ../my_soc_top/my_soc_top_postFiller_place.rpt -ignoreOutOfCore
# Filler/route repair may have changed PG connections since step21. Trim
# remaining redundant stubs, then require the unfiltered full PG report clean.
editTrim -nets {VDD VSS}
verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -error 100000 -report ../my_soc_top/my_soc_top_postFiller_pg.rpt
verify_drc -check_only default -limit 100000 -report ../my_soc_top/my_soc_top_postFiller_drc.rpt

timeDesign -postRoute -expandedViews -outDir ../my_soc_top/reports/postFiller
timeDesign -postRoute -hold -expandedViews -outDir ../my_soc_top/reports/postFiller
verifyProcessAntenna -report ../my_soc_top/my_soc_top_postFiller_antenna.rpt
verifyConnectivity -type regular -error 100000 -report ../my_soc_top/my_soc_top_postFiller_signal.rpt
saveDesign ../my_soc_top/backup/my_soc_top_postFiller.enc
