`timescale 1ns/1ps
// HAR build profile; exactly the same external port contract as Lab 3.
module simple_npu_top (
    input logic clka, rst_ni, ena, wea,
    input logic [11:0] addra,
    input logic [31:0] dina,
    output logic [31:0] douta
);
    logic [511:0] input_features;
    logic [16383:0] weight1;
    logic [1535:0] weight2;
    logic [1023:0] bias1;
    logic [191:0] bias2;
    logic [15:0] requant_mult;
    logic [4:0] requant_shift;
    wire [255:0] hidden;
    wire [191:0] scores;
    wire [2:0] class_id;
    wire [31:0] cycle_count;
    wire busy, done;
    logic error;
    logic [31:0] read_data;
    wire write_request = ena && wea;
    wire start_request = write_request && addra == 0 && dina[0];
    wire ack_request = write_request && addra == 0 && dina[1];

    har_npu_core core (
        .clk(clka), .rst_ni(rst_ni), .start(start_request && !busy),
        .ack_done(ack_request && !busy), .input_features(input_features),
        .weight1(weight1), .weight2(weight2), .bias1(bias1), .bias2(bias2),
        .requant_mult(requant_mult), .requant_shift(requant_shift),
        .busy(busy), .done(done), .hidden(hidden), .scores(scores),
        .class_id(class_id), .cycle_count(cycle_count)
    );
    always_ff @(posedge clka or negedge rst_ni) begin
        if (!rst_ni) begin
            input_features <= 0; weight1 <= 0; weight2 <= 0; bias1 <= 0; bias2 <= 0;
            requant_mult <= 1; requant_shift <= 0; error <= 0; douta <= 0;
        end else begin
            douta <= read_data;
            if (write_request) begin
                if (busy) error <= 1;
                else if (addra == 0) begin
                    if (dina[0] || dina[1]) error <= 0;
                end else if (addra == 4) begin
                    if (dina[31:16] != 0) error <= 1;
                    else requant_mult <= dina[15:0];
                end else if (addra == 5) begin
                    if (dina > 31) error <= 1;
                    else requant_shift <= dina[4:0];
                end else if (addra >= 16 && addra < 32)
                    input_features[(addra-16)*32 +: 32] <= dina;
                else if (addra >= 64 && addra < 576)
                    weight1[(addra-64)*32 +: 32] <= dina;
                else if (addra >= 576 && addra < 624)
                    weight2[(addra-576)*32 +: 32] <= dina;
                else if (addra >= 624 && addra < 656)
                    bias1[(addra-624)*32 +: 32] <= dina;
                else if (addra >= 656 && addra < 662)
                    bias2[(addra-656)*32 +: 32] <= dina;
            end
        end
    end
    always_comb begin
        read_data = 0;
        if (ena && !wea) begin
            case (addra)
                1: read_data = {29'b0, error, busy, done};
                2: read_data = {29'b0, class_id};
                3: read_data = cycle_count;
                4: read_data = {16'b0, requant_mult};
                5: read_data = {27'b0, requant_shift};
                default: begin
                    if (addra >= 16 && addra < 32) read_data = input_features[(addra-16)*32 +: 32];
                    else if (addra >= 64 && addra < 576) read_data = weight1[(addra-64)*32 +: 32];
                    else if (addra >= 576 && addra < 624) read_data = weight2[(addra-576)*32 +: 32];
                    else if (addra >= 624 && addra < 656) read_data = bias1[(addra-624)*32 +: 32];
                    else if (addra >= 656 && addra < 662) read_data = bias2[(addra-656)*32 +: 32];
                    else if (addra >= 672 && addra < 680) read_data = hidden[(addra-672)*32 +: 32];
                    else if (addra >= 704 && addra < 710) read_data = scores[(addra-704)*32 +: 32];
                end
            endcase
        end
    end
endmodule
