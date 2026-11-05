create_library_set -name lib_tt_io -timing [concat $tt_1p80v_25c_libs [list ${io_lib}tc.lib]]
create_delay_corner -name delay_tt_io -library_set lib_tt_io -rc_corner rc_tt_1p80v_25c -si_enabled false
create_analysis_view -name func_tt_io -constraint_mode func -delay_corner delay_tt_io
set_analysis_view -setup {func_tt_io} -hold {func_tt_io}
all_analysis_views -type setup
all_analysis_views -type hold
report_analysis_views
