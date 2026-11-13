#######################################################
#                                                     
#  Innovus Command Logging File                     
#  Created on Wed Nov  4 11:19:33 2026                
#                                                     
#######################################################

#@(#)CDS: Innovus v21.16-s078_1 (64bit) 12/07/2022 12:07 (Linux 3.10.0-693.el7.x86_64)
#@(#)CDS: NanoRoute 21.16-s078_1 NR221206-1807/21_16-UB (database version 18.20.600) {superthreading v2.17}
#@(#)CDS: AAE 21.16-s035 (64bit) 12/07/2022 (Linux 3.10.0-693.el7.x86_64)
#@(#)CDS: CTE 21.16-s024_1 () Dec  5 2022 05:41:45 ( )
#@(#)CDS: SYNTECH 21.16-s009_1 () Nov  9 2022 03:47:50 ( )
#@(#)CDS: CPE v21.16-s066
#@(#)CDS: IQuantus/TQuantus 21.1.1-s939 (64bit) Wed Nov 9 09:34:24 PST 2022 (Linux 3.10.0-693.el7.x86_64)

set_global _enable_mmmc_by_default_flow      $CTE::mmmc_default
suppressMessage ENCEXT-2799
setMultiCpuUsage -localCpu 1
is_common_ui_mode
restoreDesign /home/s2400011035/chip-fullstack-2026/eda_runs/uploads/20261103_int22_9970d6f/work/pnr/my_soc_top/backup/step34.enc.dat my_soc_top
report_clocks > [file join $timing_output clocks.log]
report_timing -late -to $inputs -max_paths 20 -path_type full_clock > [file join $timing_output sram_input_setup.log]
report_timing -early -to $inputs -max_paths 20 -path_type full_clock > [file join $timing_output sram_input_hold.log]
report_timing -late -from $outputs -max_paths 20 -path_type full_clock > [file join $timing_output sram_output_setup.log]
report_timing -early -from $outputs -max_paths 20 -path_type full_clock > [file join $timing_output sram_output_hold.log]
