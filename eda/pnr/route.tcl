# Actual six-metal detailed routing and native post-route parasitic extraction.
pnr4::assert_io_supplies
# Preserve an actual placement/clock-tree view before signal routing begins.
defOut -routing [file join $output_root outputs my_soc_top_postcts.def]
setAttribute -net VDDPST -skip_routing true
setAttribute -net VSSPST -skip_routing true
setDesignMode -bottomRoutingLayer METAL2 -topRoutingLayer METAL6
setNanoRouteMode -routeWithTimingDriven true -routeDesignRouteClockNetsFirst true
setExtractRCMode -engine postRoute -effortLevel low -tQuantusForPostRoute false
routeDesign
globalNetConnect VDD -type pgpin -pin VDD -all
globalNetConnect VSS -type pgpin -pin VSS -all
pnr4::assert_io_supplies
verify_drc -check_only default -limit 100000 -report [file join $output_root reports route_drc.rpt]
verifyConnectivity -type regular -error 100000 -report [file join $output_root reports route_signal_connectivity.rpt]
verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -error 100000 -report [file join $output_root reports route_power_connectivity.rpt]
verifyProcessAntenna -pgnet -report [file join $output_root reports route_antenna.rpt]
checkPlace [file join $output_root reports route_placement.rpt] -ignoreOutOfCore
timeDesign -postRoute -expandedViews -outDir [file join $output_root reports route_setup]
timeDesign -postRoute -hold -expandedViews -outDir [file join $output_root reports route_hold]
defOut -routing [file join $output_root outputs my_soc_top_routed.def]
puts PNR_ROUTE_FINISHED
