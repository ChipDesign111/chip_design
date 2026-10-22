saveDesign ../my_soc_top/backup/my_soc_top_prePostRouteHoldFix.enc
setOptMode -fixHoldAllowSetupTnsDegrade false -holdTargetSlack 0
optDesign -postRoute -hold -expandedViews -outDir ../my_soc_top/reports/postRoute_holdFix
