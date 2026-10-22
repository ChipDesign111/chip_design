# Functional netlist omits physical-only objects; LVS export retains real PG.
set outputs [file join $output_root outputs]
set raw_sdf [file join $outputs my_soc_top_tt_io.sdf.gz]
set gls_sdf [file join $outputs my_soc_top_tt_io_gls.sdf.gz]
foreach path [list $raw_sdf $gls_sdf] {
    if {[file exists $path]} {error "Refusing to overwrite an existing SDF: $path"}
}
defOut -routing [file join $outputs my_soc_top.def]
saveNetlist [file join $outputs my_soc_top_final_physical.v] -phys -excludeLeafCell -topModuleFirst
saveNetlist [file join $outputs my_soc_top_flat_lvs.v] -excludeLeafCell -flat -phys -excludeCellInst {FILL1BWP7T FILL2BWP7T FILL4BWP7T FILL8BWP7T FILL16BWP7T FILL32BWP7T FILL64BWP7T TAPCELLBWP7T PCORNER PFILLER20 PFILLER10 PFILLER5 PFILLER1 PFILLER05 PFILLER0005 PRCUT PAD60LU_OBV}
# The antenna diode has a real one-input Verilog model. Keep it so extracted
# INTERCONNECT loads and SDF endpoints match the simulation netlist exactly.
set simulation_exclude_cells {}
foreach master $functional_exclude_cells {
    if {$master ne {ANTENNABWP7T}} {lappend simulation_exclude_cells $master}
}
saveNetlist [file join $outputs my_soc_top_hier_postpnr.v] -excludeLeafCell -topModuleFirst -removePowerGround -excludeCellInst $simulation_exclude_cells
write_sdc -view func_tt_io > [file join $outputs my_soc_top.sdc]
write_sdc -path_adjust_only > [file join $outputs my_soc_top_path_adjust.tcl]
if {[file size [file join $outputs my_soc_top_path_adjust.tcl]] != 0} {
    error "Unexpected path adjustments in physical implementation"
}
if {![dbGet top.statusRCExtracted]} {extractRC}
rcOut -view func_tt_io -cUnit pF -spef [file join $outputs my_soc_top_tt_io.spef.gz]
# Keep the same explicit STA options for both exports. The only GLS option is
# -filter: clip negative propagation delays while preserving timing checks.
# The Verilog preset also recomputes parallel arcs and is deliberately avoided.
set sdf_sta_options {-min_view func_tt_io -typ_view func_tt_io -max_view func_tt_io -target_application sta -edges check_edge -collapse_internal_pins -setuphold merge_when_paired -recrem merge_when_paired -min_period_edges none -recompute_delay_calc}
write_sdf {*}$sdf_sta_options $raw_sdf
write_sdf {*}$sdf_sta_options -filter $gls_sdf
write_lef_abstract -5.8 -cutObsMinSpacing -specifyTopLayer METAL6 [file join $outputs my_soc_top.lef]
setStreamOutMode -labelAllPinShape true -virtualConnection false
streamOut [file join $outputs my_soc_top.gds.gz] -mapFile $gds_map -merge $gds_files -mode ALL -units 2000
if {[file exists [file join $pnr_script_root capture_physical.tcl]]} {
    set ::env(PHYSICAL_AUDIT_DIR) [file join $output_root reports physical_db]
    set ::env(PHYSICAL_AUDIT_STAGE) final_postroute
    source [file join $pnr_script_root capture_physical.tcl]
}
puts PNR_EXPORT_FINISHED
