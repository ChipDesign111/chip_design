# Same TT libraries and native RC characterization as the completed course Lab4.
create_constraint_mode -name func -sdc_file [file join $script_root constraints.sdc]
create_library_set -name lib_tt -timing [list $std_lib $sram_lib]
create_opcond -name opcond_tt -process 1 -voltage 1.8 -temperature 25
create_timing_condition -name timing_tt -library_sets lib_tt -opcond opcond_tt
create_rc_corner -name rc_tt -temperature 25 -cap_table $captable
create_delay_corner -name tt -rc_corner rc_tt -timing_condition timing_tt -si_enabled false
create_analysis_view -name func_tt -constraint_mode func -delay_corner tt
set_analysis_view -setup func_tt -hold func_tt
