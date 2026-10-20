saveNetlist ../my_soc_top/outputs/manual_final/my_soc_top_hier_postpnr.v -excludeLeafCell -topModuleFirst -removePowerGround -excludeCellInst {FILL1BWP7T FILL2BWP7T FILL4BWP7T FILL8BWP7T FILL16BWP7T FILL32BWP7T FILL64BWP7T TAPCELLBWP7T PCORNER PFILLER20 PFILLER10 PFILLER5 PFILLER1 PFILLER05 PFILLER0005 PRCUT PAD60LU_OBV DCAPBWP7T DCAP4BWP7T DCAP8BWP7T DCAP16BWP7T DCAP32BWP7T DCAP64BWP7T ANTENNABWP7T}
write_sdc -view func_tt_io > ../my_soc_top/outputs/manual_final/my_soc_top.sdc
write_sdc -path_adjust_only > ../my_soc_top/outputs/manual_final/my_soc_top_path_adjust.tcl
