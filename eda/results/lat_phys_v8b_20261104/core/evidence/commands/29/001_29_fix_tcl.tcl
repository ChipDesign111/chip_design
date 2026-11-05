# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
saveDesign ../my_soc_top/backup/my_soc_top_preHoldFix.enc
setOptMode -fixHoldAllowSetupTnsDegrade false
optDesign -postCTS -hold -expandedViews -outDir ../my_soc_top/reports/postCTS_holdFix

