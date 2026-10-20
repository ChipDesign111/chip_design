set_ccopt_property primary_delay_corner delay_tt_io
set_ccopt_property update_io_latency false
set_ccopt_property force_update_io_latency false
create_ccopt_clock_tree_spec -views {func_tt_io}
set_interactive_constraint_modes [all_constraint_modes -active]
set_clock_uncertainty -setup 0.47 [get_clocks {sys_clk jtag_clk}]
set_clock_uncertainty -hold 0.2 [get_clocks {sys_clk jtag_clk}]
set_input_transition 0.5 [get_ports {clk_i tck_i}]
set_interactive_constraint_modes {}
set_ccopt_property source_output_max_trans 0.5 -clock_tree sys_clk
set_ccopt_property source_output_max_trans 0.5 -clock_tree jtag_clk
set_ccopt_property source_max_capacitance 5.0 -clock_tree sys_clk
set_ccopt_property source_max_capacitance 5.0 -clock_tree jtag_clk
ccopt_design -check_prerequisites
