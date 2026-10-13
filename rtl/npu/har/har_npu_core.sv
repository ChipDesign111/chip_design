// Two inference stages, 2 FC1 tiles (16x4) : 1 FC2 tile (6x2).
// Each layer issues 16 chunks. Two hidden slots allow genuine cross-sample
// overlap in batch=2 mode. A single sample still respects the layer dependency.
module har_npu_core (
    input logic clk,rst_ni,start,ack_done,batch_two,
    input logic [511:0] input_features,input_features1,
    input logic [1023:0] bias1,
    input logic [191:0] bias2,
    input logic [15:0] requant_mult,
    input logic [4:0] requant_shift,
    output logic busy,done,
    output logic [255:0] hidden,hidden1,
    output logic [191:0] scores,scores1,
    output logic [2:0] class_id,class_id1,
    output logic [31:0] cycle_count,overlap_count,fc1_cycles,fc2_cycles,
    output wire w1_re,w2_re,
    output wire [3:0] w1_addr,
    output wire [2:0] w2_addr,
    input logic [1023:0] w1_data,
    input logic [191:0] w2_data
);
    logic s1_active,s2_active,s1_slot,s2_slot,two_q;
    logic [4:0] s1_issue,s2_issue;
    logic [1:0] hidden_valid,finished;
    logic [511:0] x_buffer[0:1];
    logic [255:0] h_buffer[0:1];
    logic [1023:0] bias1_q;
    logic [191:0] bias2_q;
    logic [15:0] mult_q;
    logic [4:0] shift_q;
    logic s1_read_valid,s1_first,s1_last,s2_read_valid,s2_first,s2_last,s2_half;
    logic [31:0] x_chunk;
    logic [15:0] h_chunk;
    wire [95:0] w2_chunk;
    wire [511:0] tile0_result,tile1_result;
    wire [191:0] tile2_result;
    wire tile0_valid,tile1_valid,tile2_valid;
    assign w1_re=s1_active && s1_issue<16;
    assign w1_addr=s1_issue[3:0];
    assign w2_re=s2_active && s2_issue<16;
    assign w2_addr=s2_issue[3:1];
    genvar n;
    generate for(n=0;n<6;n=n+1) begin: select_half
        assign w2_chunk[n*16+:16]=w2_data[n*32+s2_half*16+:16];
    end endgenerate
    har_dot_tile #(.OUTPUTS(16),.LANES(4)) fc1_tile0(
        .clk(clk),.rst_ni(rst_ni),.valid_i(s1_read_valid),.first_i(s1_first),.last_i(s1_last),
        .activation_i(x_chunk),.weight_i(w1_data[511:0]),.bias_i(bias1_q[511:0]),
        .valid_o(tile0_valid),.result_o(tile0_result));
    har_dot_tile #(.OUTPUTS(16),.LANES(4)) fc1_tile1(
        .clk(clk),.rst_ni(rst_ni),.valid_i(s1_read_valid),.first_i(s1_first),.last_i(s1_last),
        .activation_i(x_chunk),.weight_i(w1_data[1023:512]),.bias_i(bias1_q[1023:512]),
        .valid_o(tile1_valid),.result_o(tile1_result));
    har_dot_tile #(.OUTPUTS(6),.LANES(2)) fc2_tile(
        .clk(clk),.rst_ni(rst_ni),.valid_i(s2_read_valid),.first_i(s2_first),.last_i(s2_last),
        .activation_i(h_chunk),.weight_i(w2_chunk),.bias_i(bias2_q),
        .valid_o(tile2_valid),.result_o(tile2_result));
    function automatic [7:0] quant(input logic signed [31:0] v,
                                  input logic [15:0] m,input logic [4:0] s);
        logic [63:0] value;
        begin
            value=0;
            if(v>0) begin
                value={32'b0,$unsigned(v)}*{48'b0,m};
                if(s!=0) value=(value+(64'd1<<(s-1)))>>s;
            end
            quant=value>127 ? 8'd127:value[7:0];
        end
    endfunction
    function automatic [2:0] argmax(input logic [191:0] values);
        logic signed [31:0] best;
        integer j;
        begin
            best=$signed(values[31:0]);argmax=0;
            for(j=1;j<6;j=j+1)
                if($signed(values[j*32+:32])>best) begin best=$signed(values[j*32+:32]);argmax=j;end
        end
    endfunction
    integer i;
    always_ff @(posedge clk or negedge rst_ni) begin
        if(!rst_ni) begin
            busy<=0;done<=0;cycle_count<=0;overlap_count<=0;fc1_cycles<=0;fc2_cycles<=0;
            s1_active<=0;s2_active<=0;s1_slot<=0;s2_slot<=0;two_q<=0;
            s1_issue<=0;s2_issue<=0;hidden_valid<=0;finished<=0;
            s1_read_valid<=0;s2_read_valid<=0;
            s1_first<=0;s1_last<=0;s2_first<=0;s2_last<=0;s2_half<=0;
            x_chunk<=0;h_chunk<=0;bias1_q<=0;bias2_q<=0;mult_q<=0;shift_q<=0;
            x_buffer[0]<=0;x_buffer[1]<=0;h_buffer[0]<=0;h_buffer[1]<=0;
            hidden<=0;hidden1<=0;scores<=0;scores1<=0;class_id<=0;class_id1<=0;
        end else begin
            // These registers align activations/metadata with synchronous weight reads.
            s1_read_valid<=w1_re;s2_read_valid<=w2_re;
            if(w1_re) begin
                x_chunk<=x_buffer[s1_slot][s1_issue*32+:32];
                s1_first<=s1_issue==0;s1_last<=s1_issue==15;
            end
            if(w2_re) begin
                h_chunk<=h_buffer[s2_slot][s2_issue*16+:16];s2_half<=s2_issue[0];
                s2_first<=s2_issue==0;s2_last<=s2_issue==15;
            end
            if(!busy) begin
                if(start) begin
                    busy<=1;done<=0;two_q<=batch_two;cycle_count<=0;overlap_count<=0;fc1_cycles<=0;fc2_cycles<=0;
                    s1_active<=1;s2_active<=0;s1_slot<=0;s2_slot<=0;s1_issue<=0;s2_issue<=0;
                    hidden_valid<=0;finished<=0;
                    x_buffer[0]<=input_features;x_buffer[1]<=input_features1;
                    bias1_q<=bias1;bias2_q<=bias2;mult_q<=requant_mult;shift_q<=requant_shift;
                    hidden<=0;hidden1<=0;scores<=0;scores1<=0;class_id<=0;class_id1<=0;
                end else if(ack_done) done<=0;
            end else begin
                cycle_count<=cycle_count+1'b1;
                if(s1_active) fc1_cycles<=fc1_cycles+1'b1;
                if(s2_active) fc2_cycles<=fc2_cycles+1'b1;
                if(s1_active && s2_active) overlap_count<=overlap_count+1'b1;
                if(w1_re) s1_issue<=s1_issue+1'b1;
                if(w2_re) s2_issue<=s2_issue+1'b1;
                if(s1_active && tile0_valid && tile1_valid) begin
                    for(i=0;i<16;i=i+1) begin
                        h_buffer[s1_slot][i*8+:8]<=quant($signed(tile0_result[i*32+:32]),mult_q,shift_q);
                        h_buffer[s1_slot][(i+16)*8+:8]<=quant($signed(tile1_result[i*32+:32]),mult_q,shift_q);
                        if(!s1_slot) begin
                            hidden[i*8+:8]<=quant($signed(tile0_result[i*32+:32]),mult_q,shift_q);
                            hidden[(i+16)*8+:8]<=quant($signed(tile1_result[i*32+:32]),mult_q,shift_q);
                        end else begin
                            hidden1[i*8+:8]<=quant($signed(tile0_result[i*32+:32]),mult_q,shift_q);
                            hidden1[(i+16)*8+:8]<=quant($signed(tile1_result[i*32+:32]),mult_q,shift_q);
                        end
                    end
                    hidden_valid[s1_slot]<=1;
                    if(two_q && !s1_slot) begin s1_slot<=1;s1_issue<=0;end
                    else s1_active<=0;
                end
                if(!s2_active) begin
                    if(hidden_valid[0] && !finished[0]) begin s2_slot<=0;s2_active<=1;s2_issue<=0;end
                    else if(two_q && hidden_valid[1] && !finished[1]) begin s2_slot<=1;s2_active<=1;s2_issue<=0;end
                end
                if(s2_active && tile2_valid) begin
                    finished[s2_slot]<=1;s2_active<=0;
                    if(!s2_slot) begin scores<=tile2_result;class_id<=argmax(tile2_result);end
                    else begin scores1<=tile2_result;class_id1<=argmax(tile2_result);end
                    if(!two_q || s2_slot) begin busy<=0;done<=1;end
                end
            end
        end
    end
endmodule
