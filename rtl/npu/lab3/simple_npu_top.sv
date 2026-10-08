`timescale 1ns/1ps
// Frozen Lab 3 byte/word map; read response is registered, with no side effects.
module simple_npu_top (
    input logic clka, rst_ni, ena, wea,
    input logic [11:0] addra,
    input logic [31:0] dina,
    output logic [31:0] douta
);
    logic [15:0][3:0] activation, weight;
    wire [15:0][9:0] result;
    wire done;
    wire start = ena && wea && addra == 0 && dina[0];
    logic [31:0] read_data;
    simple_npu_core core (.clk(clka), .rst_ni(rst_ni), .start(start), .done(done),
        .act(activation), .wgt(weight), .out(result));
    always_ff @(posedge clka or negedge rst_ni) begin
        if (!rst_ni) begin activation <= '0; weight <= '0; douta <= '0; end
        else begin
            if (ena && wea) begin
                if (addra >= 16 && addra < 32) activation[addra-16] <= dina[3:0];
                if (addra >= 1024 && addra < 1040) weight[addra-1024] <= dina[3:0];
            end
            douta <= read_data;
        end
    end
    always_comb begin
        read_data = 0;
        if (ena && !wea) begin
            if (addra == 1) read_data = {31'b0, done};
            else if (addra >= 16 && addra < 32) read_data = {28'b0, activation[addra-16]};
            else if (addra >= 1024 && addra < 1040) read_data = {28'b0, weight[addra-1024]};
            else if (addra >= 2048 && addra < 2064) read_data = {22'b0, result[addra-2048]};
        end
    end
endmodule
