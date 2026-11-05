dbGet top.nets.name VDDPST
dbGet top.nets.name VSSPST

if {[dbGet top.nets.name VDDPST] eq "0x0"} {addNet VDDPST -power}
if {[dbGet top.nets.name VSSPST] eq "0x0"} {addNet VSSPST -ground}
globalNetConnect VDD -type pgpin -pin VDD -all -verbose
globalNetConnect VSS -type pgpin -pin VSS -all -verbose

attachTerm i_pad_N_vddio VDDPST VDDPST
attachTerm i_pad_N_poc VDDPST VDDPST
attachTerm i_pad_N_vssio VSSPST VSSPST
attachTerm i_pad_S_vddio VDDPST VDDPST
attachTerm i_pad_S_poc VDDPST VDDPST
attachTerm i_pad_S_vssio VSSPST VSSPST
attachTerm i_pad_W_vddio VDDPST VDDPST
attachTerm i_pad_W_poc VDDPST VDDPST
attachTerm i_pad_W_vssio VSSPST VSSPST
attachTerm i_pad_E_vddio VDDPST VDDPST
attachTerm i_pad_E_poc VDDPST VDDPST
attachTerm i_pad_E_vssio VSSPST VSSPST

saveNetlist ../my_soc_top/my_soc_top_pg_bound.v -phys
saveDesign ../my_soc_top/backup/my_soc_top_postPGConnect.enc
foreach sn {VDD VSS VDDPST VSSPST} {puts "SUPPLY $sn [dbGet top.nets.name $sn]"}
foreach side {N S W E} {foreach pair {{vddio VDDPST} {poc VDDPST} {vssio VSSPST}} {lassign $pair suffix pin; set it [dbGet top.insts.instTerms.name i_pad_${side}_${suffix}/$pin -p]; set nn [dbGet $it.net.name]; puts "SUPPLY_TERM i_pad_${side}_${suffix}/$pin $nn"; if {$nn ne $pin} {error "Wrong IO supply"}}}
