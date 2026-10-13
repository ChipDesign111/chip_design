`timescale 1ns/1ps
// Compatible interface and timing for the immutable Lab 3 tests.
module simple_npu_core (
    input logic clk, rst_ni, start,
    output logic done,
    input logic [15:0][3:0] act, wgt,
    output wire [15:0][9:0] out
);
    typedef enum logic [1:0] {IDLE, RUN, DONE} state_t;
    state_t state;
    logic [3:0] tick;
    wire enable = state == RUN;
    wire clear = start && state != RUN;
    wire [3:0] a_link [0:3][0:4];
    wire [3:0] b_link [0:4][0:3];
    assign done = state == DONE;
    always_ff @(posedge clk or negedge rst_ni) begin
        if (!rst_ni) begin state <= IDLE; tick <= 0; end
        else case (state)
            IDLE, DONE: if (start) begin state <= RUN; tick <= 0; end
            RUN: if (tick == 9) state <= DONE; else tick <= tick + 1'b1;
            default: begin state <= IDLE; tick <= 0; end
        endcase
    end
    genvar row, col;
    generate
        for (row=0; row<4; row=row+1) begin : rows
            wire signed [31:0] k = $signed({1'b0, tick}) - row;
            assign a_link[row][0] = enable && k >= 0 && k < 4 ? act[k*4+row] : 4'd0;
            for (col=0; col<4; col=col+1) begin : cols
                simple_npu_pe pe (
                    .clk(clk), .rst_ni(rst_ni), .clr(clear), .en(enable),
                    .a(a_link[row][col]), .b(b_link[row][col]),
                    .a_o(a_link[row][col+1]), .b_o(b_link[row+1][col]),
                    .acc(out[col*4+row])
                );
            end
        end
        for (col=0; col<4; col=col+1) begin : inputs_b
            wire signed [31:0] k = $signed({1'b0, tick}) - col;
            assign b_link[0][col] = enable && k >= 0 && k < 4 ? wgt[col*4+k] : 4'd0;
        end
    endgenerate
endmodule
