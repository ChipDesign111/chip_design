# Actual sourced body; main SRAM resolved to i_mainmem/i_sram/i_macro
dbGet top.terms.name
set prior_pads [dbGet -e top.insts.cell.baseClass pad -p2]
if {[llength $prior_pads] != 0} {error "Unexpected existing PAD"}
saveDesign ../my_soc_top/backup/my_soc_top_prePad.enc
if {[lsort [dbGet top.terms.name]] ne [lsort {clk_i rst_ni tck_i tms_i td_i td_o}]} {error "Unexpected top-level signal ports"}

