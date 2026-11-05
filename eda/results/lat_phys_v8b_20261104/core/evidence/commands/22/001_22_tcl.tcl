# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
saveDesign ../my_soc_top/backup/my_soc_top_postPowerPlan.enc
verifyConnectivity -type special -net {VDDPST VSSPST} -allPGPinPort -error 100000 -report ../my_soc_top/my_soc_top_io_pg_connectivity.rpt

