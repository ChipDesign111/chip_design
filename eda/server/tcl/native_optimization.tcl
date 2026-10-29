# Optimization-only allowance for one physical antenna load; every independent
# check, saved checkpoint and exported SDC uses the original lecture limit.
proc eda_native_opt {args} {
    global eda_antenna_fanout_reserve eda_antenna_repair_strategy rm_max_fanout rm_core_top eda_work step eda_command_index
    eda_apply_antenna_strategy
    if {$eda_antenna_fanout_reserve > 0} {
        set target [expr {$rm_max_fanout - $eda_antenna_fanout_reserve}]
        if {$target < 1} {error "Invalid physical fanout reserve"}
        set_interactive_constraint_modes [all_constraint_modes -active]
        set_max_fanout $target $rm_core_top
        set_interactive_constraint_modes {}
        puts "EDA_NATIVE_FANOUT_OPT target=$target final_limit=$rm_max_fanout command=$args"
    }
    set code [catch {uplevel 1 $args} result options]
    if {$eda_antenna_fanout_reserve > 0} {
        set_interactive_constraint_modes [all_constraint_modes -active]
        set_max_fanout $rm_max_fanout $rm_core_top
        set_interactive_constraint_modes {}
        puts "EDA_NATIVE_FANOUT_RESTORED final_limit=$rm_max_fanout"
    }
    if {$code == 0 && $eda_antenna_repair_strategy eq "native_jumpers_first" && [lindex $args 0] eq "optDesign" && [lsearch -exact $args -postRoute] >= 0} {
        # Native timing ECO routing can alter antenna geometry. Recheck the
        # actual result and repair it before the caller's independent STA/DRC.
        eda_native_antenna_repair [file join $eda_work evidence antenna_repairs [format "%02d_%03d" $step $eda_command_index]]
    }
    return -options $options $result
}
