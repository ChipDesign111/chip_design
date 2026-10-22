`timescale 1ns/1ps
// External 120ps payload-clock skew represents the observed source/sink phase
// difference. No force or disabled specify/timing check is used.
module reset_phase_tb;
    parameter real SKEW_NS = 0.120;
    logic clk_i = 0, raw_reset_ni = 0;
    wire payload_clk_i, reset_out_n;
    wire [7:0] counter;
    reset_phase_probe dut(.*);
    always #10 clk_i = ~clk_i;
    assign #(SKEW_NS) payload_clk_i = clk_i;
    always @(posedge reset_out_n)
        $display("RESET_RELEASE time_ns=%0.3f counter=%h", $realtime, counter);
    initial begin
        #40; raw_reset_ni = 1;
        #160;
        $display("RESET_PHASE_STATE counter=%h known=%0d", counter, !$isunknown(counter));
        raw_reset_ni = 0;
        #40; raw_reset_ni = 1;
        #160;
        $display("RESET_PHASE_STATE counter=%h known=%0d", counter, !$isunknown(counter));
        $display("RESET_PHASE_FINISHED");
        $finish;
    end
endmodule
