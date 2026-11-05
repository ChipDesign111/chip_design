dbGet top.terms.name
set prior_pads [dbGet -e top.insts.cell.baseClass pad -p2]
if {[llength $prior_pads] != 0} {error "Unexpected existing PAD"}
saveDesign ../my_soc_top/backup/my_soc_top_prePad.enc
