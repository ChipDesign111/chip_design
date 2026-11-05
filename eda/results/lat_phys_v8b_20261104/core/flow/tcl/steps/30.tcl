setAttribute -net VDDPST -skip_routing true
setAttribute -net VSSPST -skip_routing true
setDesignMode -bottomRoutingLayer METAL2 -topRoutingLayer METAL6
setNanoRouteMode -routeWithTimingDriven true -routeDesignRouteClockNetsFirst true
setExtractRCMode -engine postRoute -effortLevel low -tQuantusForPostRoute false
routeDesign
