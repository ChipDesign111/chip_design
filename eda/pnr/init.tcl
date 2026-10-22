setLibraryUnit -cap 1pf -time 1ns
set_global timing_derate_spatial_distance_unit 1nm
set init_verilog $netlist_file
set init_top_cell my_soc_top
set init_lef_file $lef_files
set init_mmmc_file [file join $pnr_script_root mmmc.tcl]
set init_design_uniquify 1
init_design
if {[dbGet top.name] ne "my_soc_top"} {error "Wrong imported design"}
source [file join $pnr_script_root settings.tcl]
set macro_ptr [dbGet top.insts.name $macro_instance -p]
if {$macro_ptr eq "0x0" || [llength $macro_ptr] != 1} {error "Expected main SRAM instance missing"}
if {[dbGet $macro_ptr.cell.name] ne "RA1SHD_2048x32M8"} {error "Wrong SRAM master"}
if {[llength [dbGet top.terms.name]] != 6} {error "Core must have 6 functional ports"}
checkDesign -all
saveNetlist [file join $output_root outputs pre_io.v] -excludeLeafCell -topModuleFirst -removePowerGround
