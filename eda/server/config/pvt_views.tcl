# Matched available-library PVT sets. Called after the base definitions.
# The same supplied typical RC technology is used at each temperature.
set eda_pvt_specs {
    {ss_pvt wc ss_1p62_125C 125 1.62 ss}
    {ff0_pvt bc ff_1p98_0C 0 1.98 ff0}
    {ffm40_pvt lt ff_1p98_-40C -40 1.98 ffm40}
}
foreach spec $eda_pvt_specs {
    lassign $spec corner suffix macro_suffix temp voltage short
    lappend proj(corners) $corner
    set proj($corner,P) 1
    set proj($corner,T) $temp
    set proj($corner,V) $voltage
    set libs [list ${base_lib_dir}/${std_lib}${suffix}.lib]
    foreach macro $macro_insts {
        lappend libs ${rm_macro_dirs}/${macro}/${macro}_${macro_suffix}_syn.lib
    }
    set proj(library_set,$corner) $libs
}
set proj(analysis_view,setup) [list func_tt_1p80v_25c func_ss_pvt func_ff0_pvt func_ffm40_pvt]
set proj(analysis_view,hold) $proj(analysis_view,setup)
