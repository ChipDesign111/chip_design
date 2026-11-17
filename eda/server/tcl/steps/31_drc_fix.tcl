# Run only after the CURRENT independent default DRC reports violations.
# Marker-based ECO repair can move both sides of a conflict. Repeated
# detailRoute alone can merely move a short along the SRAM boundary.
# If native ECO leaves regular-wire shorts, reroute only their CURRENT
# signal nets. No historical net names, clock/PG wires or logical nets
# are removed. The driver's bounded loop and independent audits remain.
deselectAll
setNanoRouteMode -routeSelectedNetOnly false -droutePostRouteSpreadWire false -drouteFixAntenna true
setNanoRouteMode -reset -drouteEndIteration
ecoRoute -fix_drc
verify_drc -check_only default -limit 100000 -report ../my_soc_top/my_soc_top_postAntennaFix_drc.rpt
if {[eda_drc_count ../my_soc_top/my_soc_top_postAntennaFix_drc.rpt] > 0} {
    set fd [open ../my_soc_top/my_soc_top_postAntennaFix_drc.rpt r]
    set drc_text [read $fd]; close $fd
    set short_nets {}
    foreach line [split $drc_text "\n"] {
        if {[regexp {^SHORT: .*Regular Wire of Net (\S+) & Regular Wire of Net (\S+)\s+\(} $line -> net_a net_b]} {
            foreach net [list $net_a $net_b] {
                # editDelete accepts patterns; never let a reported name
                # expand to unrelated nets. Other names use native fallback.
                if {![regexp {[*?\[\]\\]} $net]} {lappend short_nets $net}
            }
        }
    }
    set short_nets [lsort -unique $short_nets]
    if {[llength $short_nets] > 64} {error "Too many current short nets for bounded repair"}
    if {[llength $short_nets] > 0} {
        foreach net $short_nets {
            set objects [dbGet -e top.nets.name $net -p]
            if {[llength $objects] != 1 || [dbGet [lindex $objects 0].name] ne $net} {
                error "Current DRC net does not resolve exactly: $net"
            }
            puts "EDA_CURRENT_DRC_SIGNAL_REROUTE $net"
            editDelete -net $net -type Regular -use SIGNAL
        }
        ecoRoute
    } else {
        detailRoute
    }
}
verifyProcessAntenna -report ../my_soc_top/my_soc_top_postAntennaFix_antenna.rpt
verify_drc -check_only default -limit 100000 -report ../my_soc_top/my_soc_top_postAntennaFix_drc.rpt
verifyConnectivity -type regular -error 100000 -report ../my_soc_top/my_soc_top_postAntennaFix_signal.rpt
verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -error 100000 -report ../my_soc_top/my_soc_top_postAntennaFix_pg.rpt
