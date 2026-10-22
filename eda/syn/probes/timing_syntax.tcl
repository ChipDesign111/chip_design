# Empty-session option parsing probe; no RTL, library or saved design is read.
foreach cmd {
    {report_timing -early -max_paths 1}
    {report_timing -check_type hold -max_paths 1}
    {report timing -early -max_paths 1}
    {report_timing -max_paths 1}
} {
    puts "SYNTAX_PROBE_BEGIN $cmd"
    set status [catch {uplevel #0 $cmd} message]
    puts "SYNTAX_PROBE_RESULT status=$status message=$message"
    puts "SYNTAX_PROBE_END $cmd"
}
puts "TIMING_SYNTAX_FINISHED"
exit
