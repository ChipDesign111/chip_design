// Small independent circuit: async assertion, four posedge synchronizer stages,
// and an optional negedge release register. Not part of production RTL.
module reset_phase_probe (
    input logic clk_i, payload_clk_i, raw_reset_ni,
    output wire reset_out_n,
    output logic [7:0] counter
);
    logic [3:0] stages;
    wire synchronized_n = stages[3];
    always_ff @(posedge clk_i or negedge raw_reset_ni)
        if (!raw_reset_ni) stages <= 0;
        else stages <= {stages[2:0], 1'b1};
`ifdef NEGEDGE_RELEASE
    logic released_n;
    always_ff @(negedge clk_i or negedge synchronized_n)
        if (!synchronized_n) released_n <= 0;
        else released_n <= 1;
    assign reset_out_n = released_n;
`else
    assign reset_out_n = synchronized_n;
`endif
    always_ff @(posedge payload_clk_i or negedge reset_out_n)
        if (!reset_out_n) counter <= 0;
        else counter <= counter + 1'b1;
endmodule
