# Run only after the CURRENT independent default DRC reports violations.
# Whole-design detail repair can move both sides of a conflict left by
# selected-net antenna routing. All downstream audits remain mandatory.
deselectAll
setNanoRouteMode -routeSelectedNetOnly false -droutePostRouteSpreadWire false -drouteFixAntenna true
setNanoRouteMode -reset -drouteEndIteration
detailRoute
verifyProcessAntenna -report ../my_soc_top/my_soc_top_postAntennaFix_antenna.rpt
verify_drc -check_only default -limit 100000 -report ../my_soc_top/my_soc_top_postAntennaFix_drc.rpt
verifyConnectivity -type regular -error 100000 -report ../my_soc_top/my_soc_top_postAntennaFix_signal.rpt
verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -error 100000 -report ../my_soc_top/my_soc_top_postAntennaFix_pg.rpt
