# Read-only command syntax probe. No technology library or RTL is loaded.
foreach cmd {report_timing write_sdc get_nets get_object_name} {
    puts "COMMAND_HELP_BEGIN $cmd"
    help $cmd
    puts "COMMAND_HELP_END $cmd"
}
puts "COMMAND_HELP_FINISHED"
exit
