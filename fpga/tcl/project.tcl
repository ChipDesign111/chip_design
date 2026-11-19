# Recreate or open an external project using the tracked inputs and configuration.
if {$argc != 1} { error "Usage: project.tcl /external/workspace/config/project.tcl" }
source [file normalize [lindex $argv 0]]
set project_file [file join $cfg(project_dir) final_project.xpr]
if {[file exists $project_file]} {
    open_project $project_file
} else {
    create_project final_project $cfg(project_dir) -part $cfg(part)
}
set_property target_language Verilog [current_project]
set_property simulator_language Mixed [current_project]
set sources {}
set includes {}
set stream [open [file join $cfg(repo) rtl filelist.f] r]
foreach line [split [read $stream] \n] {
    set line [string trim $line]
    if {$line eq "" || [string match {//*} $line]} { continue }
    if {[string match {+incdir+*} $line]} {
        lappend includes [file join $cfg(repo) [string range $line 8 end]]
    } elseif {![string match {*cv32e40p_fp_wrapper.sv} $line]} {
        lappend sources [file join $cfg(repo) $line]
    }
}
close $stream
lappend sources [file join $cfg(repo) fpga src fpga_top.sv]
foreach source $sources {
    if {![file isfile $source]} { error "Source missing: $source" }
    if {[llength [get_files -quiet $source]] == 0} { add_files -norecurse $source }
    set_property file_type SystemVerilog [get_files $source]
}
set_property include_dirs $includes [get_filesets sources_1]
set constraints [file join $cfg(repo) fpga src fpga_top.xdc]
if {[llength [get_files -quiet $constraints]] == 0} { add_files -fileset constrs_1 -norecurse $constraints }
set_property top $cfg(top) [get_filesets sources_1]
set_property top_auto_set false [get_filesets sources_1]

if {[llength [get_ips -quiet $cfg(clock_ip)]] == 0} {
    create_ip -name clk_wiz -vendor xilinx.com -library ip -version $cfg(clock_ip_version) -module_name $cfg(clock_ip)
}
set properties {}
foreach key [lsort [array names clock_cfg]] { lappend properties CONFIG.$key $clock_cfg($key) }
set_property -dict $properties [get_ips $cfg(clock_ip)]
generate_target all [get_ips $cfg(clock_ip)]
update_compile_order -fileset sources_1

# Keep the familiar runtime synth_2/impl_2 pair; synth_1/impl_1 is preload.
if {[llength [get_runs -quiet $cfg(runtime_synth)]] == 0} {
    create_run $cfg(runtime_synth) -flow [get_property FLOW [get_runs synth_1]] -srcset sources_1 -constrset constrs_1
}
if {[llength [get_runs -quiet $cfg(runtime_impl)]] == 0} {
    create_run $cfg(runtime_impl) -parent_run $cfg(runtime_synth) -flow [get_property FLOW [get_runs impl_1]]
}
if {$cfg(mode) eq "runtime"} {
    set synth $cfg(runtime_synth)
    set impl $cfg(runtime_impl)
    set generic SRAM_INIT_FILE=
} else {
    if {![file isfile $cfg(firmware)]} { error "Preload firmware missing: $cfg(firmware)" }
    set synth $cfg(preload_synth)
    set impl $cfg(preload_impl)
    set generic SRAM_INIT_FILE=$cfg(firmware)
}
set_property strategy $cfg(synthesis_strategy) [get_runs $synth]
set_property STEPS.SYNTH_DESIGN.ARGS.DIRECTIVE $cfg(synthesis_directive) [get_runs $synth]
set_property -name {STEPS.SYNTH_DESIGN.ARGS.MORE OPTIONS} -value [list -generic $generic] -objects [get_runs $synth]
puts "FPGA_PROJECT_CONFIGURED project=$project_file mode=$cfg(mode) synth=$synth impl=$impl"
if {$cfg(stage) ne "project"} {
    reset_run $synth
    launch_runs $synth -jobs $cfg(jobs)
    wait_on_run $synth
    if {[get_property PROGRESS [get_runs $synth]] ne "100%"} { error "Synthesis failed" }
    if {$cfg(stage) eq "bitstream"} {
        reset_run $impl
        launch_runs $impl -to_step write_bitstream -jobs $cfg(jobs)
        wait_on_run $impl
        if {[get_property PROGRESS [get_runs $impl]] ne "100%"} { error "Implementation failed" }
    }
}
close_project
