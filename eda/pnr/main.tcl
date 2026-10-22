source [file join [file dirname [file normalize [info script]]] config.tcl]
cd $output_root
set invocation_id $::env(CHIP_PNR_INVOCATION)
proc save_physical_tcl_context {path} {
    set f [open $path w]
    puts $f {# Recorded helper state for this exact saved Innovus checkpoint.}
    if {[namespace exists ::pnr4]} {
        puts $f {namespace eval ::pnr4 {}}
        foreach name [lsort [info vars ::pnr4::*]] {
            if {[info exists $name]} {puts $f [list set $name [set $name]]}
        }
        foreach name [lsort [info procs ::pnr4::*]] {
            set parameters {}
            foreach argument [info args $name] {
                if {[info default $name $argument default_value]} {
                    lappend parameters [list $argument $default_value]
                } else {lappend parameters $argument}
            }
            puts $f [list proc $name $parameters [info body $name]]
        }
    }
    close $f
}
if {[info exists ::env(CHIP_PNR_RESUME)] && $::env(CHIP_PNR_RESUME) ne ""} {
    restoreDesign $::env(CHIP_PNR_RESUME) my_soc_top
    regsub {\.dat$} $::env(CHIP_PNR_RESUME) {} context_base
    set context_file ${context_base}.context.tcl
    if {[file exists $context_file]} {source $context_file} elseif {![string match init-* [file tail $context_base]]} {
        error "Missing physical Tcl context for non-init checkpoint: $context_file"
    }
    if {[file exists [file join $pnr_script_root geometry_helpers.tcl]]} {
        source [file join $pnr_script_root geometry_helpers.tcl]
    }
    source [file join $pnr_script_root settings.tcl]
}
foreach stage $::env(CHIP_PNR_STAGES) {
    puts "PNR_STAGE_BEGIN $stage"
    flush stdout
    if {[catch {
        source [file join $pnr_script_root ${stage}.tcl]
        set checkpoint [file join $output_root backup ${stage}-${invocation_id}.enc]
        saveDesign $checkpoint
        save_physical_tcl_context ${checkpoint}.context.tcl
        set f [open [file join $output_root latest_checkpoint.txt] w]
        puts $f ${checkpoint}.dat
        close $f
        set f [open [file join $output_root ${stage}-checkpoint.txt] w]
        puts $f ${checkpoint}.dat
        close $f
    } answer options]} {
        puts "PNR_STAGE_FAILED $stage: $answer"
        puts [dict get $options -errorinfo]
        flush stdout
        exit 2
    }
    puts "PNR_STAGE_COMPLETE $stage"
    flush stdout
}
puts PNR_INVOCATION_COMPLETE
exit 0
