# Discover the currently connected A7-35T instead of reusing a cached
# hardware-target serial number from a previous Vivado session.
proc har_connect_fpga {} {
    catch {close_hw_target}
    catch {disconnect_hw_server}

    connect_hw_server -url localhost:3121
    refresh_hw_server

    set targets [get_hw_targets]
    if {[llength $targets] == 0} {
        error "No JTAG targets are currently visible on localhost:3121"
    }

    foreach target $targets {
        catch {close_hw_target}

        if {[catch {current_hw_target $target} error]} {
            puts "Skipping target $target: $error"
            continue
        }

        # A stale target may open successfully but expose no devices.
        if {[catch {open_hw_target} error]} {
            puts "Cannot open target $target: $error"
        }

        if {[catch {get_hw_devices} devices]} {
            set devices {}
        }

        foreach device $devices {
            set part ""
            catch {set part [get_property PART $device]}

            if {[string match -nocase "xc7a35t*" $part] ||
                [string match -nocase "*xc7a35t*" $device]} {
                current_hw_device $device
                puts "Connected JTAG target: $target"
                puts "Current FPGA device: $device"
                return $device
            }
        }

        catch {close_hw_target}
    }

    error "No online xc7a35t device was found"
}

proc har_program_fpga {bitfile} {
    if {![file isfile $bitfile]} {
        error "Bitstream not found: $bitfile"
    }

    set device [har_connect_fpga]
    set_property PROGRAM.FILE $bitfile $device
    program_hw_devices $device
    refresh_hw_device -update_hw_probes false $device
    puts "Programmed $device with $bitfile"
}
