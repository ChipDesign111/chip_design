# Full-SoC placement after floorplan/io/power. main.tcl owns checkpoints.
pnr4::assert {[info exists pnr4::tie_exclude_file]} "Restore the power-stage Tcl context first"
pnr4::assert_io_supplies
pnr4::assert_io_geometry
pnr4::assert_io_abutment
setMultiCpuUsage -localCpu $pnr_cpus

proc pnr4::object_count {objects} {
    if {$objects eq {0x0} || $objects eq {}} {return 0}
    return [llength $objects]
}
proc pnr4::assert_clock_periods {} {
    foreach {name expected} {sys_clk 20.0 jtag_clk 100.0 virtual_jtag_tck 1000.0} {
        set clock [get_clocks $name]
        pnr4::assert {[sizeof_collection $clock]==1} "Expected exactly one SDC clock: $name"
        set period [get_property $clock period]
        pnr4::assert {[string is double -strict $period] && abs($period-$expected)<0.000001} "Clock $name period changed: $period, expected $expected ns"
    }
}
proc pnr4::placed_checks {prefix} {
    global output_root
    checkPlace [file join $output_root reports ${prefix}_placement.rpt] -ignoreOutOfCore
    set unplaced [pnr4::object_count [dbGet top.insts.pStatus unplaced -p]]
    pnr4::assert {$unplaced==0} "$prefix has $unplaced unplaced physical instances"
    pnr4::assert_io_supplies
    pnr4::assert_io_geometry
    pnr4::assert_io_abutment
    verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -error 100000 -report [file join $output_root reports ${prefix}_core_pg.rpt]
    set handle [open [file join $output_root reports ${prefix}_instance_counts.rpt] w]
    puts $handle "unplaced $unplaced"
    puts $handle "placed [pnr4::object_count [dbGet top.insts.pStatus placed -p]]"
    puts $handle "fixed [pnr4::object_count [dbGet top.insts.pStatus fixed -p]]"
    puts $handle "Intentional bond/PAD overlaps must be classified from the placement report; no core overlap is waived."
    close $handle
}
pnr4::assert_clock_periods

# Refuse to duplicate physical cells by accidentally rerunning from a completed
# placement checkpoint. A failed stage is rerun from its power checkpoint.
pnr4::assert {[pnr4::object_count [dbGet top.insts.name WELLTAP* -p]]==0} "WELLTAP instances already exist"
pnr4::assert {[pnr4::object_count [dbGet top.insts.name DECAP* -p]]==0} "DECAP instances already exist"
addWellTap -cell TAPCELLBWP7T -cellInterval 60 -checkerBoard -prefix WELLTAP
verifyWellTap -cell TAPCELLBWP7T -rule 30 -report [file join $output_root reports welltap.rpt]
addWellTap -cell DCAP4BWP7T -cellInterval 60 -skipRow 1 -prefix DECAP
globalNetConnect VDD -type pgpin -pin VDD -all
globalNetConnect VSS -type pgpin -pin VSS -all
verify_drc -check_only special -report [file join $output_root reports preplace_special_drc.rpt]

# Respect the real PG shapes and macro halo. No real scan chains are present;
# functional scan-cell inference is handled with the course's explicit modes.
setPlaceMode -place_detail_preroute_as_obs {} -place_detail_use_check_drc true
setPlaceMode -place_global_ignore_scan true -place_global_reorder_scan false
place_opt_design
checkPlace [file join $output_root reports place_before_ties.rpt] -ignoreOutOfCore

# Verify the exclusion file is exactly the twelve native IO supply endpoints.
pnr4::assert {[file readable $pnr4::tie_exclude_file]} "Missing IO supply tie exclusion file"
set handle [open $pnr4::tie_exclude_file r]
set excluded {}
foreach line [split [read $handle] \n] {
    set line [string trim $line]
    if {$line ne {}} {lappend excluded $line}
}
close $handle
set expected_exclusions {}
foreach entry $pnr4::supply_terms {
    lassign $entry instance pin net
    lappend expected_exclusions "$instance/$pin"
}
pnr4::assert {[llength $excluded]==12 && [lsort $excluded] eq [lsort $expected_exclusions]} "IO supply tie exclusions are incomplete or stale"
setTieHiLoMode -cell {TIEHBWP7T TIELBWP7T} -maxFanout 1 -maxDistance 100
addTieHiLo -cellPin {PDDW0204CDG:I PDDW0204CDG:DS PDDW0204CDG:OEN PDDW0204CDG:PE PDDW0204CDG:IE}
setTieHiLoMode -cell {TIEHBWP7T TIELBWP7T} -maxFanout 8 -maxDistance 50
addTieHiLo -keepExisting true -excludePin $pnr4::tie_exclude_file
globalNetConnect VDD -type pgpin -pin VDD -all
globalNetConnect VSS -type pgpin -pin VSS -all
refinePlace
pnr4::placed_checks postplace
pnr4::assert_clock_periods
checkFPlan -reportUtil -outFile [file join $output_root reports postplace_utilization.rpt]
report_clocks > [file join $output_root reports prects_clocks.rpt]
write_sdc -view func_tt_io [file join $output_root outputs my_soc_top_prects.sdc]
timeDesign -preCTS -expandedViews -outDir [file join $output_root reports preCTS]
timeDesign -preCTS -hold -expandedViews -outDir [file join $output_root reports preCTS]
puts "PNR_PLACE_FINISHED; inspect legal placement, core PG, and preCTS setup/hold reports"
