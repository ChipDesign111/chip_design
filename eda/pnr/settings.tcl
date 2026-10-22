# Innovus 21.16 course settings, with no path adjustments or period changes.
setMultiCpuUsage -localCpu $pnr_cpus
setDesignMode -process 180 -congEffort auto -earlyClockFlow false -expressRoute false -flowEffort standard -powerEffort low -bottomRoutingLayer METAL2 -topRoutingLayer METAL6
setAnalysisMode -analysisType onChipVariation -aocv false -cppr both -usefulSkew true
setDelayCalMode -accuracy_level 0 -advanced_pincap_mode false -equivalent_waveform_model propagation -SIAware false
set hold_fixing_cells {DEL015BWP7T DEL01BWP7T DEL02BWP7T DEL0BWP7T DEL1BWP7T DEL2BWP7T DEL3BWP7T DEL4BWP7T BUFFD0BWP7T BUFFD1BWP7T BUFFD1P5BWP7T BUFFD2BWP7T BUFFD2P5BWP7T BUFFD3BWP7T BUFFD4BWP7T BUFFD5BWP7T BUFFD6BWP7T BUFFD8BWP7T BUFFD10BWP7T BUFFD12BWP7T}
setOptMode -allEndPoints true -checkRoutingCongestion true -fixFanoutLoad true -fixHoldAllowOverlap false -fixHoldAllowResizing true -fixHoldAllowSetupTnsDegrade false -fixHoldOnExcludedClockNets true -fixSISlew true -highEffortOptCells $hold_fixing_cells -holdFixingCells $hold_fixing_cells -holdTargetSlack 0 -maxDensity 0.75 -multiBitFlopOpt false -postRouteAreaReclaim none -postRouteSetupRecovery auto -powerEffort none -restruct true -setupTargetSlack 0 -timeDesignNumPaths 50 -unfixClkInstForOpt true -usefulSkew true -usefulSkewCCOpt extreme -usefulSkewPostRoute true -usefulSkewPreCTS true
setPlaceMode -place_design_floorplan_mode false -place_design_refine_place true -place_detail_legalization_inst_gap 2 -place_detail_use_check_drc true -place_global_clock_power_driven true -place_global_cong_effort auto -place_global_place_io_pins false -place_global_timing_effort high -place_global_ignore_scan true -place_global_reorder_scan false
setTieHiLoMode -cell {TIEHBWP7T TIELBWP7T} -maxFanout 8
setAddRingMode -avoid_short true
setUsefulSkewMode -maxAllowedDelay 2.0 -noBoundary false -useCells $hold_fixing_cells
set_ccopt_property update_io_latency false
set_ccopt_property force_update_io_latency false
set_ccopt_property enable_all_views_for_io_latency_update true
set_ccopt_property max_fanout 16
set_ccopt_property effort high
set_ccopt_property buffer_cells {CKBD0BWP7T CKBD1BWP7T CKBD2BWP7T CKBD3BWP7T CKBD4BWP7T CKBD6BWP7T CKBD8BWP7T CKBD10BWP7T CKBD12BWP7T}
set_ccopt_property inverter_cells {INVD0BWP7T INVD1BWP7T INVD1P5BWP7T INVD2BWP7T INVD2P5BWP7T INVD3BWP7T INVD4BWP7T INVD5BWP7T INVD6BWP7T INVD8BWP7T INVD10BWP7T INVD12BWP7T}
set_ccopt_property clock_gating_cells {CKLNQD1BWP7T CKLNQD2BWP7T CKLNQD4BWP7T CKLNQD6BWP7T CKLNQD8BWP7T CKLHQD1BWP7T CKLHQD2BWP7T CKLHQD4BWP7T CKLHQD6BWP7T CKLHQD8BWP7T}
set_ccopt_property primary_delay_corner delay_tt_io
set_ccopt_mode -cts_use_min_max_path_delay false -cts_target_slew 0.5 -cts_target_skew 0.15
setNanoRouteMode -drouteFixAntenna true -drouteUseMultiCutViaEffort low -routeAntennaCellName ANTENNABWP7T -routeDesignRouteClockNetsFirst true -routeInsertAntennaDiode true -routeReserveSpaceForMultiCut false -routeWithLithoDriven false -routeWithTimingDriven true
setFillerMode -diffCellViol true -ecoMode true -fitGap true -scheme locationFirst
set_global timing_set_clock_source_to_output_as_data true
set timing_disable_lib_pulsewidth_checks false
