# Independent library-initialization diagnostic. No RTL is read or synthesized.
# Required environment: PROBE_CONFIG points at an existing read-only run_config.
# PROBE_MODE: full | empty | units | preload_std | preload_both | nolef_units | lef_after | full_lef_after
source $::env(PROBE_CONFIG)
set mode $::env(PROBE_MODE)
set_db information_level 6
set_db max_cpus_per_server 1
puts "LIBRARY_PROBE_BEGIN mode=$mode"
if {$mode ni {nolef_units lef_after full_lef_after}} { set_db lef_library $lef_files }
if {$mode eq "preload_std"} { read_libs $std_lib }
if {$mode eq "preload_both"} { read_libs [list $std_lib $sram_lib] }
set sdc [file join [pwd] probe.sdc]
if {$mode in {full preload_std preload_both full_lef_after}} {
    set sdc [file join $script_root constraints.sdc]
} else {
    set fh [open $sdc w]
    if {$mode eq "units" || $mode eq "nolef_units"} {
        puts $fh {set_units -time ns -capacitance pF}
    }
    close $fh
}
set mmmc [file join [pwd] probe_mmmc.tcl]
set fh [open $mmmc w]
puts $fh "create_constraint_mode -name func -sdc_file [list $sdc]"
puts $fh {create_library_set -name lib_tt -timing [list $std_lib $sram_lib]}
puts $fh {create_opcond -name opcond_tt -process 1 -voltage 1.8 -temperature 25}
puts $fh {create_timing_condition -name timing_tt -library_sets lib_tt -opcond opcond_tt}
puts $fh {create_rc_corner -name rc_tt -temperature 25 -cap_table $captable}
puts $fh {create_delay_corner -name tt -rc_corner rc_tt -timing_condition timing_tt -si_enabled false}
puts $fh {create_analysis_view -name func_tt -constraint_mode func -delay_corner tt}
puts $fh {set_analysis_view -setup func_tt -hold func_tt}
close $fh
read_mmmc $mmmc
if {$mode in {lef_after full_lef_after}} { set_db lef_library $lef_files }
report_units
report_messages -all
puts "LIBRARY_PROBE_FINISHED mode=$mode"
exit
