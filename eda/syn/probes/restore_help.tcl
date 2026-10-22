# Read-only syntax discovery; never restores or changes a design.
foreach query {read_db read_design report_signoff_timing report_timing_summary report} {
    puts "RESTORE_HELP_BEGIN $query"
    if {[catch {help $query} err]} { puts "RESTORE_HELP_ERROR $err" }
    puts "RESTORE_HELP_END $query"
}
puts "RESTORE_HELP_FINISHED"
exit
