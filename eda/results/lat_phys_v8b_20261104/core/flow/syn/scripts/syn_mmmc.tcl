#####################################################################################
# Description:  Logic Synthesis MMMC Definition
# Modifier:     Mingxuan Li <mingxuanli_siris@163.com> [Peking University]
# Acknowledge:  Columbia University, System Level Design Group
#####################################################################################

create_constraint_mode -name func -sdc_file $proj(constraints,func)

foreach corner $proj(corners) {
  create_library_set -name lib_${corner} -timing $proj(library_set,$corner)
  create_opcond -name opcond_${corner} -process $proj($corner,P) -voltage $proj($corner,V) -temperature $proj($corner,T)
  create_timing_condition -name timing_${corner} -library_sets lib_${corner} -opcond opcond_${corner}
  create_rc_corner -name rc_${corner} -temperature $proj($corner,T) -cap_table $rm_captable_file
  create_delay_corner -name $corner -rc_corner rc_${corner} -timing_condition timing_${corner} -si_enabled false
  create_analysis_view -name func_${corner} -constraint_mode func -delay_corner $corner
}

set_analysis_view -setup $proj(analysis_view,setup) -hold $proj(analysis_view,hold)
