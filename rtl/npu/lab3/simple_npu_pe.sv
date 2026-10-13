`timescale 1ns/1ps
// Lab 3 compatibility profile: unsigned 4-bit output-stationary PE.
module simple_npu_pe (
    input logic clk, rst_ni, clr, en,
    input logic [3:0] a, b,
    output logic [3:0] a_o, b_o,
    output logic [9:0] acc
);
    wire [7:0] product = a * b;
    always_ff @(posedge clk or negedge rst_ni) begin
        if (!rst_ni) begin acc <= '0; a_o <= '0; b_o <= '0; end
        else if (clr) begin acc <= '0; a_o <= '0; b_o <= '0; end
        else if (en) begin
            acc <= acc + {2'b0, product};
            a_o <= a;
            b_o <= b;
        end
    end
endmodule
