# Read the CURRENT independent antenna report; no historical net list is used.
set ant_fd [open ../my_soc_top/my_soc_top_postRoute_antenna.rpt r]
set ant_text [read $ant_fd]
close $ant_fd
set antenna_nets {}
foreach ant_line [split $ant_text "\n"] {
    if {[regexp {^(\S+) \([0-9]+\)$} [string trimright $ant_line] -> ant_net]} {
        lappend antenna_nets $ant_net
    }
}
set antenna_nets [lsort -unique $antenna_nets]
if {[regexp {Number of nets violated:\s+([0-9]+)} $ant_text -> ant_count]} {
    if {[llength $antenna_nets] != $ant_count} {error "Antenna report/net-count mismatch; inspect report"}
} elseif {[string first "No Violations Found" $ant_text] >= 0} {
    set ant_count 0
} else {error "Unrecognized antenna report; inspect manually"}
puts "CURRENT_ANTENNA_NETS $antenna_nets"
if {$ant_count > 0} {
    setNanoRouteMode -droutePostRouteSpreadWire false -drouteFixAntenna true
    setNanoRouteMode -reset -drouteEndIteration
    deselectAll
    foreach ant_net $antenna_nets {selectNet $ant_net}
    detailRoute -select
    deselectAll
}
verifyProcessAntenna -report ../my_soc_top/my_soc_top_postAntennaFix_antenna.rpt
verify_drc -check_only default -limit 100000 -report ../my_soc_top/my_soc_top_postAntennaFix_drc.rpt
verifyConnectivity -type regular -error 100000 -report ../my_soc_top/my_soc_top_postAntennaFix_signal.rpt
verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -error 100000 -report ../my_soc_top/my_soc_top_postAntennaFix_pg.rpt
saveDesign ../my_soc_top/backup/my_soc_top_postRoute_antennaFixed.enc
