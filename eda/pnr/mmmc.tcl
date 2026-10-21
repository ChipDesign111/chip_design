# Same nominal TT views; actual extracted interconnect is selected after route.
create_library_set -name lib_tt_io -timing [list $std_lib $sram_lib $io_lib]
create_rc_corner -name rc_tt -cap_table $captable -T 25
create_delay_corner -name delay_tt_io -library_set lib_tt_io -rc_corner rc_tt
create_constraint_mode -name func -sdc_files [list $sdc_file]
create_analysis_view -name func_tt_io -constraint_mode func -delay_corner delay_tt_io
set_analysis_view -setup {func_tt_io} -hold {func_tt_io}
