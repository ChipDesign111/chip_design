# Run from the fpga directory in WSL, with GDB connected to OpenOCD :3333.
# Disconnect so the Tcl batch runner is the sole client controlling the hart.
# This wrapper does not need Python support inside GDB.
disconnect
shell python3 firmware_batch.py --run
set $soc_batch_exit = $_shell_exitcode
target extended-remote :3333
maintenance flush register-cache
if $soc_batch_exit != 0
  printf "FPGA batch did not fully pass (exit=%d); see console output and any saved summary.md/result.json.\n", $soc_batch_exit
end
