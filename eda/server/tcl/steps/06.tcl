create_library_set -name lib_tt_io -timing [concat $tt_1p80v_25c_libs [list ${io_lib}tc.lib]]
create_delay_corner -name delay_tt_io -library_set lib_tt_io -rc_corner rc_tt_1p80v_25c -si_enabled false
create_analysis_view -name func_tt_io -constraint_mode func -delay_corner delay_tt_io
set_analysis_view -setup {func_tt_io} -hold {func_tt_io}
if {[info exists eda_enable_pvt] && $eda_enable_pvt} {
    set eda_io_views {func_tt_io}
    foreach spec $eda_pvt_specs {
        lassign $spec corner suffix macro_suffix temp voltage short
        create_library_set -name lib_${short}_io -timing [concat $proj(library_set,$corner) [list ${io_lib}${suffix}.lib]]
        create_delay_corner -name delay_${short}_io -library_set lib_${short}_io -rc_corner rc_${corner} -si_enabled false
        create_analysis_view -name func_${short}_io -constraint_mode func -delay_corner delay_${short}_io
        lappend eda_io_views func_${short}_io
    }
    set_analysis_view -setup $eda_io_views -hold $eda_io_views
}
all_analysis_views -type setup
all_analysis_views -type hold
report_analysis_views
