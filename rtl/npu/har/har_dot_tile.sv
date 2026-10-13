// Output-stationary tile: registered signed products -> reduction/accumulation.
// First/last flags travel with the data; a new tile may immediately follow.
module har_dot_tile #(
    parameter integer OUTPUTS=16, LANES=4
)(
    input logic clk, rst_ni, valid_i, first_i, last_i,
    input logic [LANES*8-1:0] activation_i,
    input logic [OUTPUTS*LANES*8-1:0] weight_i,
    input logic [OUTPUTS*32-1:0] bias_i,
    output logic valid_o,
    output logic [OUTPUTS*32-1:0] result_o
);
    logic valid_q, first_q, last_q;
    logic signed [15:0] products [0:OUTPUTS-1][0:LANES-1];
    logic signed [31:0] acc [0:OUTPUTS-1];
    genvar o,k;
    generate for(o=0;o<OUTPUTS;o=o+1) begin: outputs
        wire signed [31:0] partial [0:LANES];
        assign partial[0]=first_q ? $signed(bias_i[o*32+:32]) : acc[o];
        for(k=0;k<LANES;k=k+1) begin: lanes
            assign partial[k+1]=partial[k]+$signed({{16{products[o][k][15]}},products[o][k]});
            always_ff @(posedge clk)
                if(valid_i)
                    products[o][k] <= $signed(activation_i[k*8+:8]) *
                                      $signed(weight_i[(o*LANES+k)*8+:8]);
        end
        always_ff @(posedge clk or negedge rst_ni) begin
            if(!rst_ni) begin acc[o]<=0; result_o[o*32+:32]<=0; end
            else if(valid_q) begin
                acc[o]<=partial[LANES];
                if(last_q) result_o[o*32+:32]<=partial[LANES];
            end
        end
    end endgenerate
    always_ff @(posedge clk or negedge rst_ni) begin
        if(!rst_ni) begin valid_q<=0;first_q<=0;last_q<=0;valid_o<=0;end
        else begin
            valid_q<=valid_i;first_q<=first_i;last_q<=last_i;
            valid_o<=valid_q && last_q;
        end
    end
endmodule
