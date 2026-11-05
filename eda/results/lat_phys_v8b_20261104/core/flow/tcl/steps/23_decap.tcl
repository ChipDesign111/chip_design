addWellTap -cell DCAP4BWP7T -cellInterval 60 -skipRow 1 -prefix DECAP
globalNetConnect VDD -type pgpin -pin VDD -all
globalNetConnect VSS -type pgpin -pin VSS -all
verify_drc -check_only special -report ../my_soc_top/my_soc_top_postPhysCells_pg_drc.rpt
verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -error 100000 -report ../my_soc_top/my_soc_top_postPhysCells_pg_connectivity.rpt

saveDesign ../my_soc_top/backup/my_soc_top_postPhysCells.enc
