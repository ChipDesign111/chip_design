write_lef_abstract -5.8 -cutObsMinSpacing -specifyTopLayer METAL6 ../my_soc_top/outputs/manual_final/my_soc_top.lef
setStreamOutMode -labelAllPinShape true -virtualConnection false
if {[llength $gds_list] != 4} {error "Expected four native GDS inputs"}
foreach g $gds_list {if {![file exists $g]} {error "Missing native GDS: $g"}; puts "NATIVE_GDS $g"}
if {![file exists $rm_lef_layer_map]} {error "Missing GDS map"}
streamOut ../my_soc_top/outputs/manual_final/my_soc_top.gds.gz -mapFile $rm_lef_layer_map -merge $gds_list -mode ALL -units 2000
