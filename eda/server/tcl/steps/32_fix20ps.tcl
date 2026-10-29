setOptMode -fixHoldAllowSetupTnsDegrade false -holdTargetSlack 0.02
eda_native_opt optDesign -postRoute -hold -expandedViews -outDir ../my_soc_top/reports/postRoute_holdAuto
