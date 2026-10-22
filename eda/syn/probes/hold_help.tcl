# Read-only discovery of installed Genus reporting commands.
foreach query {help *hold* *timing*} {
    puts "HELP_QUERY_BEGIN $query"
    if {[catch {help $query} err]} { puts "HELP_QUERY_ERROR $err" }
    puts "HELP_QUERY_END $query"
}
puts "HOLD_HELP_FINISHED"
exit
