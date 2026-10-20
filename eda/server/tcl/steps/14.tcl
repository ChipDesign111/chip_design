createPhysicalPin clk_i -net clk_i -layer METAL4 -rect {310 1798 320 1799}
createPhysicalPin rst_ni -net rst_ni -layer METAL4 -rect {1410 1798 1420 1799}
createPhysicalPin tck_i -net tck_i -layer METAL4 -rect {260 1 270 2}
createPhysicalPin tms_i -net tms_i -layer METAL4 -rect {460 1 470 2}
createPhysicalPin td_i -net td_i -layer METAL4 -rect {1410 1 1420 2}
createPhysicalPin td_o -net td_o -layer METAL4 -rect {1610 1 1620 2}

createPGPin VDD -net VDD -geom METAL4 910 1798 920 1799
createPGPin VSS -net VSS -geom METAL4 610 1798 620 1799
createPGPin VDDPST -net VDDPST -geom METAL4 1110 1798 1120 1799
createPGPin VSSPST -net VSSPST -geom METAL4 810 1798 820 1799
defOut ../my_soc_top/my_soc_top_physicalPins.def
saveDesign ../my_soc_top/backup/my_soc_top_postPhysicalPins.enc

fit
dumpToGIF ../../evidence/14_floorplan.gif
