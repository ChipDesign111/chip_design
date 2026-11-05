addIoFiller -cell {PFILLER20 PFILLER10 PFILLER5 PFILLER1 PFILLER05 PFILLER0005} -prefix IOF_TOP -side top -fillerOrient R180
addIoFiller -cell {PFILLER20 PFILLER10 PFILLER5 PFILLER1 PFILLER05 PFILLER0005} -prefix IOF_BOTTOM -side bottom -fillerOrient R0
addIoFiller -cell {PFILLER20 PFILLER10 PFILLER5 PFILLER1 PFILLER05 PFILLER0005} -prefix IOF_LEFT -side left -fillerOrient R270
addIoFiller -cell {PFILLER20 PFILLER10 PFILLER5 PFILLER1 PFILLER05 PFILLER0005} -prefix IOF_RIGHT -side right -fillerOrient R90

foreach prefix {IOF_TOP IOF_BOTTOM IOF_LEFT IOF_RIGHT} {puts "IO_FILLER $prefix [llength [dbGet -e top.insts.name ${prefix}*]]"}
defOut ../my_soc_top/my_soc_top_postIOFiller.def
