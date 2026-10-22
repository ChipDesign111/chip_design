# Read-only metadata collector for a completed Innovus stage. This does not
# place, route, change constraints, reconnect pins, or save/restore a design.
# The calling flow must export its DEF/netlist/reports from this same completed
# stage and bind those files to frozen hashes in audit_physical.py's config.
if {![info exists ::env(PHYSICAL_AUDIT_DIR)]} {
    error "Set PHYSICAL_AUDIT_DIR before sourcing capture_physical.tcl"
}
set audit_capture_dir [file normalize $::env(PHYSICAL_AUDIT_DIR)]
file mkdir $audit_capture_dir
set audit_capture_file [open [file join $audit_capture_dir physical_snapshot.tsv] w]
puts $audit_capture_file "schema\tchip-design-physical-snapshot-v1"
puts $audit_capture_file "timestamp_utc\t[clock format [clock seconds] -gmt true -format {%Y-%m-%dT%H:%M:%SZ}]"
if {[info exists ::env(PHYSICAL_AUDIT_STAGE)]} {
    puts $audit_capture_file "stage\t$::env(PHYSICAL_AUDIT_STAGE)"
}
puts $audit_capture_file "top\t[dbGet top.name]"
puts $audit_capture_file "die_box_um\t[dbGet top.fPlan.box]"
puts $audit_capture_file "core_box_um\t[dbGet top.fPlan.coreBox]"
puts $audit_capture_file "instance_count\t[llength [dbGet top.insts.name]]"
foreach audit_capture_port {clk_i rst_ni tck_i tms_i td_i td_o} {
    set audit_capture_term [dbGet top.terms.name $audit_capture_port -p]
    if {$audit_capture_term eq {0x0}} {error "Missing functional port $audit_capture_port"}
    puts $audit_capture_file "signal_port\t$audit_capture_port\t[dbGet $audit_capture_term.net.name]"
}
foreach audit_capture_supply {VDD VSS VDDPST VSSPST} {
    set audit_capture_net [dbGet top.nets.name $audit_capture_supply -p]
    if {$audit_capture_net eq {0x0}} {error "Missing power net $audit_capture_supply"}
    puts $audit_capture_file "supply_net\t$audit_capture_supply\t[dbGet $audit_capture_net.name]"
}
foreach audit_capture_master {RA1SHD_2048x32M8 PDDW0204CDG PVDD1CDG PVSS1CDG PVDD2CDG PVSS2CDG PVDD2POC PCORNER PAD60LU_OBV} {
    set audit_capture_insts [dbGet top.insts.cell.name $audit_capture_master -p2]
    if {$audit_capture_insts eq {0x0}} {continue}
    foreach audit_capture_inst $audit_capture_insts {
        puts $audit_capture_file "instance\t[dbGet $audit_capture_inst.name]\t$audit_capture_master\t[dbGet $audit_capture_inst.box]\t[dbGet $audit_capture_inst.orient]\t[dbGet $audit_capture_inst.pStatus]"
        foreach audit_capture_pin [dbGet $audit_capture_inst.instTerms] {
            if {$audit_capture_pin eq {0x0}} {continue}
            set audit_capture_pin_name [dbGet $audit_capture_pin.name]
            set audit_capture_pin_net [dbGet $audit_capture_pin.net.name]
            puts $audit_capture_file "pin\t$audit_capture_pin_name\t$audit_capture_pin_net"
        }
    }
}
close $audit_capture_file
puts "PHYSICAL_METADATA_CAPTURED [file join $audit_capture_dir physical_snapshot.tsv]"
