verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -noAntenna -error 100000 -report ../my_soc_top/my_soc_top_pg_noDangling.rpt
defOut -routing ../my_soc_top/my_soc_top_postM1.def
fit
dumpToGIF ../../evidence/21_powerplan.gif
