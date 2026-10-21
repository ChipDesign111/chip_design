# Full-SoC physical inputs. Licensed views remain in the course environment.
set pnr_script_root [file dirname [file normalize [info script]]]
set project_root [file dirname [file dirname $pnr_script_root]]
set output_root [file normalize $::env(CHIP_PNR_OUTPUT)]
set pdk_root /lec/pdk/tsmc180
if {[info exists ::env(CHIP_PNR_PDK)]} {set pdk_root $::env(CHIP_PNR_PDK)}
set sram_root /lec/lab4/soc_cv32e40p_template_pnr-stu/src/macro/RA1SHD_2048x32M8
if {[info exists ::env(CHIP_PNR_SRAM)]} {set sram_root $::env(CHIP_PNR_SRAM)}
set synthesis_root [file join $project_root eda work asic-resetfall synthesis]
if {[info exists ::env(CHIP_PNR_SYNTHESIS)]} {set synthesis_root $::env(CHIP_PNR_SYNTHESIS)}
set netlist_file [file join $synthesis_root outputs my_soc_top_postsyn.v]
set sdc_file [file join $synthesis_root outputs my_soc_top.sdc]
set die_size 3400.32
if {[info exists ::env(CHIP_PNR_DIE_SIZE)]} {set die_size $::env(CHIP_PNR_DIE_SIZE)}
set macro_instance i_mainmem/i_sram/i_macro
set pnr_cpus 8
if {[info exists ::env(CHIP_PNR_CPUS)]} {set pnr_cpus $::env(CHIP_PNR_CPUS)}
set std_digital [file join $pdk_root tcb018gbwp7t_290a TSMCHOME digital]
set io_digital [file join $pdk_root tpd018nv_280a TSMCHOME digital]
set bond_digital [file join $pdk_root tpb018v_180a TSMCHOME digital]
set std_lib [file join $std_digital Front_End timing_power_noise NLDM tcb018gbwp7t_270a tcb018gbwp7ttc.lib]
set io_lib [file join $io_digital Front_End timing_power_noise NLDM tpd018nv_280a tpd018nvtc.lib]
set sram_lib [file join $sram_root RA1SHD_2048x32M8_tt_1p8_25C_syn.lib]
set std_lef [file join $std_digital Back_End lef tcb018gbwp7t_270a lef tcb018gbwp7t_6lm.lef]
set io_lef [file join $io_digital Back_End lef tpd018nv_280a mt_2 6lm lef tpd018nv_6lm.lef]
set io_ant_lef [file join $io_digital Back_End lef tpd018nv_280a mt_2 6lm lef antenna_6lm.lef]
set bond_lef [file join $bond_digital Back_End lef tpb018v_180a cup 6lm lef tpb018v_6lm.lef]
set lef_files [list $std_lef $io_lef $io_ant_lef $bond_lef [file join $sram_root RA1SHD_2048x32M8.vclef] [file join $sram_root RA1SHD_2048x32M8_ant.lef]]
set captable [file join $std_digital Back_End lef tcb018gbwp7t_270a techfiles captable t018lo_1p6m_typical.captable]
set gds_map [file join $std_digital Back_End lef tcb018gbwp7t_270a techfiles gds2.map]
set gds_files [list [file join $std_digital Back_End gds tcb018gbwp7t_270a tcb018gbwp7t.gds] [file join $sram_root RA1SHD_2048x32M8.gds] [file join $io_digital Back_End gds tpd018nv_280a mt_2 6lm tpd018nv.gds] [file join $bond_digital Back_End gds tpb018v_180a cup 6lm tpb018v.gds]]
foreach dir {reports outputs backup images} {file mkdir [file join $output_root $dir]}
foreach f [concat [list $netlist_file $sdc_file $std_lib $io_lib $sram_lib $captable $gds_map] $lef_files $gds_files] {
    if {![file readable $f]} {error "Missing physical input: $f"}
}
set material_fd [open [file join $output_root actual_material_inputs.txt] w]
foreach f [concat [list $std_lib $io_lib $sram_lib $captable $gds_map] $lef_files $gds_files] {puts $material_fd [file normalize $f]}
close $material_fd
set init_pwr_net VDD
set init_gnd_net VSS
set functional_exclude_cells {FILL1BWP7T FILL2BWP7T FILL4BWP7T FILL8BWP7T FILL16BWP7T FILL32BWP7T FILL64BWP7T TAPCELLBWP7T PCORNER PFILLER20 PFILLER10 PFILLER5 PFILLER1 PFILLER05 PFILLER0005 PRCUT PAD60LU_OBV DCAPBWP7T DCAP4BWP7T DCAP8BWP7T DCAP16BWP7T DCAP32BWP7T DCAP64BWP7T ANTENNABWP7T}
