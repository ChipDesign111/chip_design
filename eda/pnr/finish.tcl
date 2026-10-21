# Preserve setup while fixing hold. A 20 ps optimization margin avoids accepting
# the two sub-report-precision negative paths left after CTS; SDC is unchanged.
setOptMode -fixHoldAllowSetupTnsDegrade false -holdTargetSlack 0.02
optDesign -postRoute -expandedViews -outDir [file join $output_root reports final_setup_opt]
optDesign -postRoute -hold -expandedViews -outDir [file join $output_root reports final_hold_opt]
optDesign -postRoute -drv -expandedViews -outDir [file join $output_root reports final_drv_opt]
globalNetConnect VDD -type pgpin -pin VDD -all
globalNetConnect VSS -type pgpin -pin VSS -all
setFillerMode -core {FILL64BWP7T FILL32BWP7T FILL16BWP7T FILL8BWP7T FILL4BWP7T FILL2BWP7T FILL1BWP7T} -corePrefix FILLER -createRows false -diffCellViol true -ecoMode true -fitGap true -scheme locationFirst -honorPrerouteAsObs false -check_signal_drc true -add_fillers_with_drc false
addFiller
globalNetConnect VDD -type pgpin -pin VDD -all
globalNetConnect VSS -type pgpin -pin VSS -all
# Only after all core/tie/clock/filler PG pins have been placed: remove true
# geometric PG stubs, preserving a restorable pre-trim database and report.
set pretrim_checkpoint [file join $output_root backup pre_pg_trim-${invocation_id}.enc]
saveDesign $pretrim_checkpoint
save_physical_tcl_context ${pretrim_checkpoint}.context.tcl
verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -error 100000 -report [file join $output_root reports pretrim_power_connectivity.rpt]
editTrim -nets VDD
editTrim -nets VSS
pnr4::assert_io_supplies
pnr4::assert_io_geometry
checkPlace [file join $output_root reports final_placement.rpt] -ignoreOutOfCore
verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -error 100000 -report [file join $output_root reports final_power_connectivity.rpt]
verifyConnectivity -type special -net {VDDPST VSSPST} -allPGPinPort -error 100000 -report [file join $output_root reports final_io_power_connectivity.rpt]
verifyConnectivity -type regular -error 100000 -report [file join $output_root reports final_signal_connectivity.rpt]
verify_drc -check_only default -limit 100000 -report [file join $output_root reports final_drc.rpt]
verifyProcessAntenna -pgnet -report [file join $output_root reports final_antenna.rpt]
verifyWellTap -cell TAPCELLBWP7T -rule 30 -report [file join $output_root reports final_welltap.rpt]
timeDesign -postRoute -expandedViews -outDir [file join $output_root reports final_setup]
timeDesign -postRoute -hold -expandedViews -outDir [file join $output_root reports final_hold]
report_timing -late -max_paths 50 > [file join $output_root reports final_setup_paths.rpt]
report_timing -early -max_paths 50 > [file join $output_root reports final_hold_paths.rpt]
puts PNR_FINISH_OPTIMIZATION_FINISHED
