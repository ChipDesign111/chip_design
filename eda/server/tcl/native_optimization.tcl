# Optimization-only allowance for one physical antenna diode load. All saved
# checkpoints, exported SDC and independent checks retain the lecture limit.
# These entry points run outside interactive constraint mode, like the original
# flow. No net names, cell edits or exception lists are used.
proc eda_native_opt {args} {
    global eda_antenna_fanout_reserve rm_max_fanout rm_core_top
    if {$eda_antenna_fanout_reserve == 0} {return [uplevel 1 $args]}
    set target [expr {$rm_max_fanout - $eda_antenna_fanout_reserve}]
    if {$target < 1} {error "Invalid physical fanout reserve"}
    set_interactive_constraint_modes [all_constraint_modes -active]
    set_max_fanout $target $rm_core_top
    set_interactive_constraint_modes {}
    puts "EDA_NATIVE_FANOUT_OPT target=$target final_limit=$rm_max_fanout command=$args"
    set code [catch {uplevel 1 $args} result options]
    # Restore even when the native optimizer fails; never export the soft goal
    # as a new acceptance condition. Preserve the native command's error.
    set_interactive_constraint_modes [all_constraint_modes -active]
    set_max_fanout $rm_max_fanout $rm_core_top
    set_interactive_constraint_modes {}
    puts "EDA_NATIVE_FANOUT_RESTORED final_limit=$rm_max_fanout"
    return -options $options $result
}
