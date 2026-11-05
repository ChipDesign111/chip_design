# Read the completed physical database. Retain real antenna diode instances
# so the SDF interconnect endpoints have matching objects. No ECO is performed.
setMultiCpuUsage -localCpu 1
source [file join $eda_work pnr my_soc_top backup step34.enc]
saveNetlist [file join $sim_inputs netlist.v] -excludeLeafCell -topModuleFirst -removePowerGround -excludeCellInst {FILL1BWP7T FILL2BWP7T FILL4BWP7T FILL8BWP7T FILL16BWP7T FILL32BWP7T FILL64BWP7T TAPCELLBWP7T PCORNER PFILLER20 PFILLER10 PFILLER5 PFILLER1 PFILLER05 PFILLER0005 PRCUT PAD60LU_OBV DCAPBWP7T DCAP4BWP7T DCAP8BWP7T DCAP16BWP7T DCAP32BWP7T DCAP64BWP7T}
puts "POSTSIM_VIEW_EXPORTED_NO_ECO"
exit 0
