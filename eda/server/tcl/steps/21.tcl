saveDesign ../my_soc_top/backup/my_soc_top_preM1_M4M5.enc
sroute -nets {VDD VSS} -connect {corePin} -corePinLayer {METAL1} -corePinTarget {firstAfterRowEnd} -layerChangeRange {METAL1 METAL4} -allowLayerChange 1 -allowJogging 0 -targetViaLayerRange {METAL1 METAL4} -crossoverViaLayerRange {METAL1 METAL4}
# All macro, pad and core PG connections now exist. Remove only redundant
# floating wire ends back to their nearest electrical connection; retain pins.
# Innovus 21.16 editTrim is the native special-wire cleanup operation.
editTrim -nets {VDD VSS}
verify_drc -check_only special -report ../my_soc_top/my_soc_top_pg_drc.rpt
verifyConnectivity -type special -net {VDD VSS} -allPGPinPort -error 100000 -report ../my_soc_top/my_soc_top_pg_connectivity.rpt

saveDesign ../my_soc_top/backup/my_soc_top_postM1.enc
