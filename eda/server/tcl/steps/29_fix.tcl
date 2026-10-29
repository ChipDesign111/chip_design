saveDesign ../my_soc_top/backup/my_soc_top_preHoldFix.enc
setOptMode -fixHoldAllowSetupTnsDegrade false
eda_native_opt optDesign -postCTS -hold -expandedViews -outDir ../my_soc_top/reports/postCTS_holdFix
