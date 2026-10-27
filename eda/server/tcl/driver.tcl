# One fresh Innovus process per request. Checkpoints are committed only after
# the current step's independent audit succeeds.
cd [file join $eda_work pnr logs]
file mkdir [file join $eda_work pnr generated]
proc eda_picture {name} {
    global eda_headless eda_work
    if {!$eda_headless} {
        fit
        dumpToGIF [file join $eda_work evidence $name]
    } else {
        puts "EDA_SCREENSHOT_SKIPPED_HEADLESS $name"
    }
}
proc eda_eval {name body} {
    global eda_work step eda_command_index eda_sram
    incr eda_command_index
    set folder [file join $eda_work evidence commands [format %02d $step]]
    file mkdir $folder
    regsub -all {[^A-Za-z0-9_]} $name _ safe_name
    set record [file join $folder [format %03d_%s.tcl $eda_command_index $safe_name]]
    set fd [open $record w]
    puts $fd "# Actual sourced body; main SRAM resolved to $eda_sram"
    if {[info exists ::eda_antenna_report]} {puts $fd "# Current antenna report: $::eda_antenna_report"}
    puts $fd $body
    close $fd
    if {$step>=24} {eda_apply_slew_scope}
    uplevel #0 $body
}
proc eda_run {name} {
    global eda_work eda_sram
    set p [file join $eda_work pnr generated $name]
    set fd [open $p r]
    set body [read $fd]
    close $fd
    set body [string map [list i_mainmem/i_mainmem $eda_sram] $body]
    eda_eval $name $body
}
proc eda_timing_bad {directory {mode all}} {
    set files [glob -nocomplain [file join $directory *.summary] [file join $directory *.summary.gz]]
    if {[llength $files] == 0} {error "Missing timing summary: $directory"}
    set bad 0
    foreach p $files {
        set fd [open $p rb]; set data [read $fd]; close $fd
        if {[file extension $p] eq ".gz"} {set data [zlib gunzip $data]}
        if {$mode ne "all" && [string first "$mode mode" $data] < 0} {continue}
        if {![regexp {Violating Paths:\|\s*([0-9]+)} $data -> count]} {error "Unrecognized timing summary: $p"}
        incr bad $count
        foreach row [split $data "\n"] {
            if {[regexp {\|\s*max_\w+\s*\|\s*([0-9]+)\s*\([0-9]+\)\s*\|[^|]*\|\s*([0-9]+)\s*\([0-9]+\)} $row -> real total]} {
                incr bad $real
                incr bad $total
            }
        }
    }
    return $bad
}
proc eda_drc_count {path} {
    set fd [open $path r]; set text [read $fd]; close $fd
    if {[regexp {Total Violations\s*:\s*([0-9]+)\s+Viols\.} $text -> count]} {
        if {[string first "No DRC violations were found" $text] >= 0} {error "Conflicting DRC report: $path"}
        return $count
    }
    if {[string first "No DRC violations were found" $text] >= 0} {return 0}
    error "Unrecognized DRC report: $path"
}
proc eda_hold_margin_bad {directory} {
    global eda_min_hold_slack
    set seen 0
    foreach p [glob -nocomplain [file join $directory *.summary] [file join $directory *.summary.gz]] {
        set fd [open $p rb];set data [read $fd];close $fd
        if {[file extension $p] eq ".gz"} {set data [zlib gunzip $data]}
        if {[string first "Hold mode" $data]<0} {continue}
        if {![regexp {WNS \(ns\):\|\s*([-0-9.]+)} $data -> wns]} {error "Missing hold WNS: $p"}
        incr seen
        if {$wns < $eda_min_hold_slack} {return 1}
    }
    if {$seen!=1} {error "Missing or ambiguous hold margin summary: $directory"}
    return 0
}
if {[catch {
    if {$eda_last == 0} {
        source [file join $eda_work pnr scripts init_pnr.tcl]
    } else {
        source [file join $eda_work config user_define.tcl]
        source [file join $eda_work config global_define.tcl]
        set checkpoint [file join $eda_work pnr my_soc_top backup [format step%02d.enc $eda_last]]
        if {![file exists $checkpoint]} {error "Missing completed-step checkpoint: $checkpoint"}
        if {![file isdirectory ${checkpoint}.dat]} {error "Missing checkpoint data: ${checkpoint}.dat"}
        # saveDesign writes a loader Tcl at .enc and the actual database in
        # .enc.dat. Source its loader; restoreDesign expects the data directory.
        source $checkpoint
        source [file join $eda_work pnr scripts init_pnr_standard.tcl]
        if {$eda_last >= 30} {
            setExtractRCMode -engine postRoute -effortLevel low -tQuantusForPostRoute false
            extractRC
        }
    }
    if {!$eda_headless} {win}
    source [file join $eda_work flow config repair.tcl]
    source [file join $eda_work flow tcl fanout.tcl]
    source [file join $eda_work flow tcl slew_scope.tcl]
    set sram_objects [dbGet -e top.insts.cell.name RA1SHD_2048x32M8 -p2]
    if {[llength $sram_objects] != 1} {error "Expected exactly one native main SRAM macro"}
    set eda_sram [dbGet [lindex $sram_objects 0].name]
    # Query/import does not need a fabricated nominal Die. Generate all
    # physical coordinates only after floorPlan reports its measured box.
    if {$eda_last < 2} {
        file copy -force [file join $eda_work flow tcl steps 01.tcl] [file join $eda_work pnr generated 01.tcl]
        set sf [open [file join $eda_work pnr generated 02.tcl] w]
        puts $sf {floorPlan -coreMarginsBy die -site core7T -s $eda_core_size $eda_core_size 150 150 150 150}
        close $sf
    } else {
        set die [lindex [dbGet top.fPlan.box] 0]
        exec $eda_python [file join $eda_work flow bin flow.py] geometry --work $eda_work --die {*}$die
    }
    for {set step [expr {$eda_last+1}]} {$step <= $eda_until} {incr step} {
        puts [format "EDA_BEGIN_STEP %02d" $step]
        exec $eda_python [file join $eda_work flow bin flow.py] begin-step --work $eda_work --step $step
        set eda_command_index 0
        switch $step {
            2 {
                eda_run 02.tcl
                set die [lindex [dbGet top.fPlan.box] 0]
                exec $eda_python [file join $eda_work flow bin flow.py] geometry --work $eda_work --die {*}$die
            }
            12 {eda_run 12.tcl; eda_run 12_check.tcl}
            15 {eda_run 15.tcl; eda_run 15_save.tcl}
            17 {eda_run 17.tcl; eda_run 17_check.tcl}
            21 {eda_run 21.tcl; eda_run 21_check.tcl}
            23 {eda_run 23_tap.tcl; eda_run 23_decap.tcl}
            26 {
                eda_run 26.tcl
                eda_eval 26_hold {timeDesign -preCTS -hold -expandedViews -outDir ../my_soc_top/reports/preCTS}
            }
            27 {eda_run 27.tcl; eda_run 27_verify.tcl}
            29 {
                if {[eda_timing_bad ../my_soc_top/reports/postCTS Hold] > 0 || [eda_hold_margin_bad ../my_soc_top/reports/postCTS]} {
                    eda_eval 29_hold_mode [list setOptMode -maxDensity $eda_hold_opt_max_density -fixHoldAllowSetupTnsDegrade false -holdTargetSlack $eda_hold_target]
                    eda_run 29_fix.tcl
                }
                eda_run 29_check.tcl
                eda_eval 29_setup_density_restore [list setOptMode -maxDensity $eda_opt_max_density]
            }
            31 {
                eda_run 31_check.tcl
                set eda_antenna_report ../my_soc_top/my_soc_top_postRoute_antenna.rpt
                for {set iteration 0} {$iteration < $eda_repair_iterations} {incr iteration} {
                    eda_run 31_fix.tcl
                    # Selected-net antenna repair can conflict with a neighbor.
                    # Preserve its independent reports before any global repair.
                    set repair_dir [file join $eda_work evidence route_repair 31 $iteration]
                    file mkdir $repair_dir
                    foreach suffix {drc antenna signal pg} {
                        file copy -force ../my_soc_top/my_soc_top_postAntennaFix_${suffix}.rpt [file join $repair_dir before_${suffix}.rpt]
                    }
                    if {[eda_drc_count ../my_soc_top/my_soc_top_postAntennaFix_drc.rpt] > 0} {
                        eda_run 31_drc_fix.tcl
                    }
                    set eda_antenna_report ../my_soc_top/my_soc_top_postAntennaFix_antenna.rpt
                    set fd [open $eda_antenna_report r]; set ant_data [read $fd]; close $fd
                    set ant_clean [expr {[string first "No Violations Found" $ant_data] >= 0 || [regexp {Number of nets violated:\s+0\y} $ant_data]}]
                    if {$ant_clean && [eda_drc_count ../my_soc_top/my_soc_top_postAntennaFix_drc.rpt] == 0} {break}
                }
            }
            32 {
                eda_eval 32_extractRC {extractRC}
                eda_run 32_initial.tcl
                for {set iteration 0} {$iteration < $eda_repair_iterations} {incr iteration} {
                    eda_eval 32_setup_density [list setOptMode -maxDensity $eda_opt_max_density]
                    set current_dir [expr {$iteration == 0 ? "../my_soc_top/reports/postRoute" : "../my_soc_top/reports/postRoute_holdAuto_check"}]
                    if {[eda_fix_fanout $current_dir] > 0} {set current_dir ../my_soc_top/reports/postRoute_fanout_check}
                    set bad [eda_timing_bad $current_dir]
                    if {$bad == 0 && ![eda_hold_margin_bad $current_dir]} {break}
                    if {[eda_timing_bad $current_dir Setup] > 0} {
                        eda_eval 32_setup_opt {optDesign -postRoute -expandedViews -outDir ../my_soc_top/reports/postRoute_setupAuto}
                    }
                    eda_eval 32_hold_mode [list setOptMode -maxDensity $eda_hold_opt_max_density -fixHoldAllowSetupTnsDegrade false -holdTargetSlack $eda_hold_target]
                    eda_eval 32_hold_opt {optDesign -postRoute -hold -expandedViews -outDir ../my_soc_top/reports/postRoute_holdAuto}
                    eda_run 32_check.tcl
                }
                # Independent final checks even if no optimization was needed.
                eda_eval 32_setup_density_restore [list setOptMode -maxDensity $eda_opt_max_density]
                eda_run 32_check.tcl
            }
            34 {
                eda_eval 34_extractRC {extractRC}
                foreach part {34_1.tcl 34_2.tcl 34_3.tcl 34_4.tcl 34_5.tcl} {eda_run $part}
                eda_eval 34_picture {eda_picture 34_final_layout.gif}
            }
            default {eda_run [format %02d.tcl $step]}
        }
        set sf [open [file join $eda_work evidence current_macro.txt] w]
        puts $sf $eda_sram; close $sf
        saveDesign [file join $eda_work pnr my_soc_top backup [format step%02d.enc $step]]
        exec $eda_python [file join $eda_work flow bin flow.py] audit-step --work $eda_work --step $step
        set progress [file join $eda_work evidence last_step.txt]
        set sf [open ${progress}.tmp w]; puts $sf $step; close $sf
        file rename -force ${progress}.tmp $progress
        puts [format "EDA_COMPLETED_STEP %02d" $step]
    }
    puts "EDA_REQUEST_COMPLETE"
} error options]} {
    puts stderr "EDA_STAGE_FAILED: $error"
    puts stderr [dict get $options -errorinfo]
    exit 1
}
exit 0
