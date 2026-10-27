# Implementation choice, not a timing exception. Preserve RTL register enables
# as data muxes and DFFs instead of using timing-sensitive E/SE/CN/SA controls.
# These families were checked against this PDK's native Liberty next_state:
# EDF/SEDF use E; SDF/GSDF use SE; DFK uses synchronous CN/SN; DFX uses SA.
# Ordinary DFFs, including native asynchronous-reset DFFs, remain available.
set eda_controlled_ff_families {EDF* SDF* SEDF* GSDF* DFK* DFX*}

proc eda_register_mapping_record {tool count} {
    set path [file join $::PROJECT_ROOT evidence register_mapping_${tool}.json]
    file mkdir [file dirname $path]
    set fd [open $path w]
    puts $fd [format {{"mapping":"%s","tool":"%s","avoided_library_cells":%d,"timing_exceptions_added":false}} $::eda_enable_mapping $tool $count]
    close $fd
    puts "EDA_REGISTER_MAPPING tool=$tool mode=$::eda_enable_mapping avoided=$count"
}

proc eda_apply_register_mapping_genus {} {
    if {$::eda_enable_mapping ne "mux_dff"} {
        eda_register_mapping_record genus 0
        return
    }
    set_db use_scan_seqs_for_non_dft false
    set cells {}
    foreach pattern $::eda_controlled_ff_families {
        set cells [concat $cells [get_db lib_cells */$pattern]]
    }
    set cells [lsort -unique $cells]
    if {[llength $cells] == 0} {error "Register mapping policy matched no native library cells"}
    set_db $cells .avoid true
    foreach value [get_db $cells .avoid] {
        if {!$value} {error "Genus register mapping option was not applied"}
    }
    eda_register_mapping_record genus [llength $cells]
}

proc eda_apply_register_mapping_innovus {} {
    if {$::eda_enable_mapping ne "mux_dff"} {
        eda_register_mapping_record innovus 0
        return
    }
    set cells {}
    foreach pattern $::eda_controlled_ff_families {
        set cells [concat $cells [dbGet -e head.libCells.name $pattern]]
    }
    set cells [lsort -unique $cells]
    if {[llength $cells] == 0} {error "Register mapping policy matched no physical library cells"}
    foreach name $cells {setDontUse $name true}
    foreach name $cells {
        foreach value [dbGet [dbGet head.libCells.name $name -p].dontUse] {
            if {!$value} {error "Innovus register mapping option was not applied: $name"}
        }
    }
    eda_register_mapping_record innovus [llength $cells]
}
