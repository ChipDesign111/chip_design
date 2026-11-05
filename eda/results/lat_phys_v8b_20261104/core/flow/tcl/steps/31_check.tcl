saveDesign ../my_soc_top/backup/my_soc_top_postRoute_raw.enc
verify_drc -check_only default -limit 100000 -report ../my_soc_top/my_soc_top_postRoute_drc.rpt
verifyConnectivity -type regular -error 100000 -report ../my_soc_top/my_soc_top_postRoute_signal_connectivity.rpt
verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -error 100000 -report ../my_soc_top/my_soc_top_postRoute_pg.rpt
verifyProcessAntenna -report ../my_soc_top/my_soc_top_postRoute_antenna.rpt
