`timescale 1ns/1ps
// One signed MAC reused by a 64 -> 32 -> 6 MLP. No trained model is embedded.
module har_npu_core (
    input logic clk, rst_ni, start, ack_done,
    input logic [511:0] input_features,
    input logic [16383:0] weight1,
    input logic [1535:0] weight2,
    input logic [1023:0] bias1,
    input logic [191:0] bias2,
    input logic [15:0] requant_mult,
    input logic [4:0] requant_shift,
    output wire busy, done,
    output logic [255:0] hidden,
    output logic [191:0] scores,
    output logic [2:0] class_id,
    output logic [31:0] cycle_count
);
    typedef enum logic [2:0] {IDLE, FC1, SAVE1, FC2, SAVE2, ARGMAX, DONE} state_t;
    state_t state;
    logic [5:0] neuron, item;
    logic signed [31:0] accumulator;
    logic signed [7:0] operand_a, operand_b;
    logic signed [15:0] product;
    logic signed [31:0] extended_product;
    integer scan;
    logic signed [31:0] best;
    logic [2:0] best_index;

    assign busy = state != IDLE && state != DONE;
    assign done = state == DONE;
    always_comb begin
        operand_a = 0;
        operand_b = 0;
        if (state == FC1) begin
            operand_a = $signed(input_features[item*8 +: 8]);
            operand_b = $signed(weight1[(neuron*64+item)*8 +: 8]);
        end else if (state == FC2) begin
            operand_a = $signed(hidden[item*8 +: 8]);
            operand_b = $signed(weight2[(neuron*32+item)*8 +: 8]);
        end
        product = operand_a * operand_b;
        extended_product = {{16{product[15]}}, product};
    end

    function automatic [7:0] requant_relu(
        input logic signed [31:0] value,
        input logic [15:0] multiplier,
        input logic [4:0] shift
    );
        logic [63:0] scaled;
        begin
            if (value <= 0) requant_relu = 0;
            else begin
                scaled = {32'b0, $unsigned(value)} * {48'b0, multiplier};
                if (shift != 0)
                    scaled = (scaled + (64'd1 << (shift-1))) >> shift;
                requant_relu = scaled > 127 ? 8'd127 : scaled[7:0];
            end
        end
    endfunction

    always_ff @(posedge clk or negedge rst_ni) begin
        if (!rst_ni) begin
            state <= IDLE; neuron <= 0; item <= 0; accumulator <= 0;
            hidden <= 0; scores <= 0; class_id <= 0; cycle_count <= 0;
        end else begin
            if (busy) cycle_count <= cycle_count + 1'b1;
            case (state)
                IDLE, DONE: begin
                    if (start) begin
                        state <= FC1; neuron <= 0; item <= 0;
                        accumulator <= $signed(bias1[0 +: 32]);
                        cycle_count <= 0;
                    end else if (ack_done) state <= IDLE;
                end
                FC1: begin
                    accumulator <= accumulator + extended_product;
                    if (item == 63) state <= SAVE1;
                    else item <= item + 1'b1;
                end
                SAVE1: begin
                    hidden[neuron*8 +: 8] <= requant_relu(accumulator, requant_mult, requant_shift);
                    item <= 0;
                    if (neuron == 31) begin
                        state <= FC2; neuron <= 0;
                        accumulator <= $signed(bias2[0 +: 32]);
                    end else begin
                        state <= FC1; neuron <= neuron + 1'b1;
                        accumulator <= $signed(bias1[(neuron+1)*32 +: 32]);
                    end
                end
                FC2: begin
                    accumulator <= accumulator + extended_product;
                    if (item == 31) state <= SAVE2;
                    else item <= item + 1'b1;
                end
                SAVE2: begin
                    scores[neuron*32 +: 32] <= accumulator;
                    item <= 0;
                    if (neuron == 5) state <= ARGMAX;
                    else begin
                        state <= FC2; neuron <= neuron + 1'b1;
                        accumulator <= $signed(bias2[(neuron+1)*32 +: 32]);
                    end
                end
                ARGMAX: begin
                    best = $signed(scores[0 +: 32]);
                    best_index = 0;
                    for (scan=1; scan<6; scan=scan+1)
                        if ($signed(scores[scan*32 +: 32]) > best) begin
                            best = $signed(scores[scan*32 +: 32]);
                            best_index = scan;
                        end
                    class_id <= best_index;
                    state <= DONE;
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
