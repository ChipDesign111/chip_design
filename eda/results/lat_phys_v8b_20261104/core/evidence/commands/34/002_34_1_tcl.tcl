# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
# Current antenna report: ../my_soc_top/my_soc_top_postAntennaFix_antenna.rpt
file mkdir ../my_soc_top/outputs/manual_final
saveDesign ../my_soc_top/backup/my_soc_top_postPinLabels.enc
defOut -routing ../my_soc_top/outputs/manual_final/my_soc_top.def

