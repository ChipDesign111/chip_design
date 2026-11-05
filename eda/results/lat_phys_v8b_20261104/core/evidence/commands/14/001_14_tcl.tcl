# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
createPhysicalPin clk_i -net clk_i -layer METAL4 -rect {310.000000 1945.840000 320.000000 1946.840000}
createPhysicalPin rst_ni -net rst_ni -layer METAL4 -rect {1410.000000 1945.840000 1420.000000 1946.840000}
createPhysicalPin tck_i -net tck_i -layer METAL4 -rect {260.000000 1.000000 270.000000 2.000000}
createPhysicalPin tms_i -net tms_i -layer METAL4 -rect {460.000000 1.000000 470.000000 2.000000}
createPhysicalPin td_i -net td_i -layer METAL4 -rect {1410.000000 1.000000 1420.000000 2.000000}
createPhysicalPin td_o -net td_o -layer METAL4 -rect {1610.000000 1.000000 1620.000000 2.000000}
createPGPin VDD -net VDD -geom METAL4 910.000000 1945.840000 920.000000 1946.840000
createPGPin VSS -net VSS -geom METAL4 610.000000 1945.840000 620.000000 1946.840000
createPGPin VDDPST -net VDDPST -geom METAL4 1110.000000 1945.840000 1120.000000 1946.840000
createPGPin VSSPST -net VSSPST -geom METAL4 810.000000 1945.840000 820.000000 1946.840000
defOut ../my_soc_top/my_soc_top_physicalPins.def
eda_picture 14_floorplan.gif

