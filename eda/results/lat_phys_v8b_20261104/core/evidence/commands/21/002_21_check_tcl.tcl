# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -noAntenna -error 100000 -report ../my_soc_top/my_soc_top_pg_noDangling.rpt
defOut -routing ../my_soc_top/my_soc_top_postM1.def

eda_picture 21_powerplan.gif
