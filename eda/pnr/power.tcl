# Native teaching PDK PG construction. Source after io.tcl.
# Regions are derived from the loaded design and placed IO/SRAM geometry.
pnr4::assert {[llength $pnr4::io_pads]==34} "Source io.tcl first"
foreach {net kind} {VDD power VSS ground VDDPST power VSSPST ground} {
    if {[dbGet top.nets.name $net] eq {0x0}} {addNet $net -$kind}
}
globalNetConnect VDD -type pgpin -pin VDD -all -verbose
globalNetConnect VSS -type pgpin -pin VSS -all -verbose
set supply_exclusion [open $pnr4::tie_exclude_file w]
foreach side {N S W E} {
    foreach {suffix pin} {vddio VDDPST poc VDDPST vssio VSSPST} {
        set instance [dict get $pnr4::io_supply_pads $side $suffix]
        attachTerm $instance $pin $pin
        lappend pnr4::supply_terms [list $instance $pin $pin]
        puts $supply_exclusion "$instance/$pin"
    }
}
close $supply_exclusion
proc pnr4::assert_io_supplies {} {
    variable supply_terms
    pnr4::assert {[llength $supply_terms]==12} "Expected twelve independent native-IO supply endpoints"
    foreach entry $supply_terms {
        lassign $entry instance pin net
        pnr4::assert {[dbGet [pnr4::iterm $instance $pin].net.name] eq $net} "IO supply was detached: $instance/$pin"
    }
}
pnr4::assert_io_supplies

# External labels land in the same native outer M4 port band as the course
# geometry; derive every rectangle from its PAD's actual placed box.
lassign $pnr4::die dx0 dy0 dx1 dy1
dict for {port record} $pnr4::signal_map {
    lassign [pnr4::box [pnr4::inst [dict get $record pad]]] x0 y0 x1 y1
    if {abs($y1-$dy1)<$pnr4::tol} {
        set rectangle [list [expr {$x0+10}] [expr {$dy1-2}] [expr {$x0+20}] [expr {$dy1-1}]]
    } else {
        set rectangle [list [expr {$x0+10}] [expr {$dy0+1}] [expr {$x0+20}] [expr {$dy0+2}]]
    }
    createPhysicalPin $port -net [dict get $record ext_net] -layer METAL4 -rect $rectangle
}
foreach {net suffix} {VDD vdd_1 VSS vss_1 VDDPST vddio VSSPST vssio} {
    set instance [dict get $pnr4::io_supply_pads N $suffix]
    lassign [pnr4::box [pnr4::inst $instance]] x0 y0 x1 y1
    createPGPin $net -net $net -geom METAL4 [expr {$x0+10}] [expr {$dy1-2}] [expr {$x0+20}] [expr {$dy1-1}]
}
setDesignMode -bottomRoutingLayer METAL2 -topRoutingLayer METAL6
deselectAll
setAddRingMode -reset
setAddRingMode -avoid_short true -stacked_via_bottom_layer METAL1 -stacked_via_top_layer METAL5
addRing -nets {VDD VSS} -type core_rings -follow core -layer {top METAL5 bottom METAL5 left METAL4 right METAL4} -width 10 -spacing 2 -offset 5 -center 0
selectInst $macro_instance
addRing -nets {VDD VSS} -type block_rings -around selected -layer {top METAL5 bottom METAL5 left METAL4 right METAL4} -width 4 -spacing 2 -offset 10 -center 0
deselectAll
setAddStripeMode -reset
setAddStripeMode -break_at {block_ring outer_ring} -allow_jog none -stacked_via_bottom_layer METAL4 -stacked_via_top_layer METAL5 -orthogonal_only false
addStripe -nets {VDD VSS} -layer METAL4 -direction vertical -width 2 -spacing 1 -set_to_set_distance 20 -start_from left -start_offset 8 -block_ring_bottom_layer_limit METAL4 -block_ring_top_layer_limit METAL5 -padcore_ring_bottom_layer_limit METAL4 -padcore_ring_top_layer_limit METAL5
addStripe -nets {VDD VSS} -layer METAL5 -direction horizontal -width 4 -spacing 2 -set_to_set_distance 30 -start_from top -start_offset 1 -block_ring_bottom_layer_limit METAL4 -block_ring_top_layer_limit METAL5 -padcore_ring_bottom_layer_limit METAL4 -padcore_ring_top_layer_limit METAL5
setSrouteMode -blockPinConnectRingPinCorners true
sroute -nets {VDD VSS} -connect {blockPin} -inst [list $macro_instance] -blockPin useLef -blockPinWidthRange {0.001 1000} -blockPinLayerRange {METAL3 METAL4} -blockPinTarget {blockring} -layerChangeRange {METAL3 METAL5} -allowLayerChange 1 -allowJogging 1 -targetViaLayerRange {METAL3 METAL5} -crossoverViaLayerRange {METAL3 METAL5}
set pnr4::macro_box [pnr4::box [pnr4::inst $macro_instance]]
lassign $pnr4::macro_box mx0 my0 mx1 my1
set vdd_access [list $mx0 [expr {$my0-14}] $mx1 [expr {$my1+14}]]
set vss_access [list $mx0 [expr {$my0-20}] $mx1 [expr {$my1+20}]]
set macro_cross [list [expr {$mx0-20}] [expr {$my0+10}] [expr {$mx1+20}] [expr {$my1-8.85}]]
foreach region [list $vdd_access $vss_access $macro_cross] {pnr4::inside $region $pnr4::core "SRAM PG access region"}
setAddStripeMode -reset
setAddStripeMode -break_at none -allow_jog none -stacked_via_bottom_layer METAL4 -stacked_via_top_layer METAL6 -orthogonal_only false -remove_floating_stripe_over_block false
foreach {net offset region} [list VDD 14 $vdd_access VSS 22 $vss_access] {
    addStripe -nets [list $net] -layer METAL6 -direction vertical -width 4 -spacing 4 -set_to_set_distance 40 -start_from left -start_offset $offset -area $region -block_ring_bottom_layer_limit METAL4 -block_ring_top_layer_limit METAL5 -padcore_ring_bottom_layer_limit METAL4 -padcore_ring_top_layer_limit METAL5
}
setAddStripeMode -reset
setAddStripeMode -break_at none -allow_jog none -stacked_via_bottom_layer METAL3 -stacked_via_top_layer METAL6 -orthogonal_only false -split_vias true -remove_floating_stripe_over_block false
addStripe -nets {VDD VSS} -layer METAL5 -direction horizontal -width 4 -spacing 2 -set_to_set_distance 30 -start_from top -start_offset 15.68 -area $macro_cross -block_ring_bottom_layer_limit METAL4 -block_ring_top_layer_limit METAL5 -padcore_ring_bottom_layer_limit METAL4 -padcore_ring_top_layer_limit METAL5

# Keep only the inner 35 um of the *actual* core-supply PAD boxes in the
# pad-access window. The provided PVSS1CDG M2 core port reaches 27.525 um
# outward from its core-facing edge; this includes it with routing clearance.
set pad_left $dx1; set pad_bottom $dy1; set pad_right $dx0; set pad_top $dy0
foreach side {N S W E} {
    foreach suffix {vdd_1 vdd_2 vss_1 vss_2} {
        lassign [pnr4::box [pnr4::inst [dict get $pnr4::io_supply_pads $side $suffix]]] x0 y0 x1 y1
        switch $side {
            N {set pad_top [expr {max($pad_top,$y0+35)}]}
            S {set pad_bottom [expr {min($pad_bottom,$y1-35)}]}
            W {set pad_left [expr {min($pad_left,$x1-35)}]}
            E {set pad_right [expr {max($pad_right,$x0+35)}]}
        }
    }
}
set pnr4::pad_route_area [list $pad_left $pad_bottom $pad_right $pad_top]
pnr4::inside $pnr4::pad_route_area $pnr4::die "Core-supply PAD access window"
setSrouteMode -reset
setSrouteMode -padPinSplit {10 0.6}
sroute -nets {VDD VSS} -connect {padPin} -area $pnr4::pad_route_area -connectInsideArea -padPinTarget {ring} -padPinPortConnect {allPort allGeom} -padPinLayerRange {METAL2 METAL2} -layerChangeRange {METAL2 METAL5} -allowLayerChange 1 -allowJogging 1 -targetViaLayerRange {METAL2 METAL5} -crossoverViaLayerRange {METAL2 METAL5} -detailed_log
sroute -nets {VDD VSS} -connect {corePin} -corePinLayer {METAL1} -corePinTarget {firstAfterRowEnd} -layerChangeRange {METAL1 METAL4} -allowLayerChange 1 -allowJogging 0 -targetViaLayerRange {METAL1 METAL4} -crossoverViaLayerRange {METAL1 METAL4}
globalNetConnect VDD -type pgpin -pin VDD -all
globalNetConnect VSS -type pgpin -pin VSS -all
pnr4::assert_io_supplies
pnr4::assert_io_geometry
pnr4::assert_io_abutment
verify_drc -check_only special -report [file join $output_root reports power_special_drc.rpt]
verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -error 100000 -report [file join $output_root reports power_core_connectivity.rpt]
verifyConnectivity -type special -net {VDDPST VSSPST} -allPGPinPort -error 100000 -report [file join $output_root reports power_native_io_connectivity.rpt]
set report [open [file join $output_root reports power_geometry.rpt] w]
foreach {name value} [list die $pnr4::die core $pnr4::core macro $pnr4::macro_box vdd_access $vdd_access vss_access $vss_access macro_cross $macro_cross pad_access $pnr4::pad_route_area] {puts $report "$name $value"}
puts $report "VDDPST/VSSPST use the provided native GDS rails and abutting PAD/filler geometry. Their LEF abstracts omit routed rail shapes; no-routing diagnostics require the independent native-GDS/DEF audit."
puts $report "Pre-placement M1 followpin endpoints must be rechecked after placement/CTS and final routing."
close $report
saveNetlist [file join $output_root outputs my_soc_top_post_power.v] -phys
defOut -routing [file join $output_root outputs my_soc_top_post_power.def]
pnr4::checkpoint power
puts "PNR_POWER_FINISHED core=$pnr4::core SRAM=$pnr4::macro_box; inspect DRC/connectivity reports"
