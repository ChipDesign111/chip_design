# W8A4 SoC Innovus MMMC: current design constraints and TT library/RC views.
# This file defines timing objects only; it does not execute implementation stages.
create_constraint_mode -name func -sdc_files $proj(constraints,func)
foreach corner $proj(corners) {
    create_library_set -name lib_${corner} -timing $proj(library_set,$corner)
    create_rc_corner -name rc_${corner} -temperature $proj($corner,T) -cap_table $rm_captable_file
    create_delay_corner -name $corner -library_set lib_${corner} -rc_corner rc_${corner} -si_enabled false
    create_analysis_view -name func_${corner} -constraint_mode func -delay_corner $corner
}
set_analysis_view -setup $proj(analysis_view,setup) -hold $proj(analysis_view,hold)
