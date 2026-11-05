// INT8 64->32->6. Tile: two FC1 input columns (64B), or one FC2 column
// (6B padded to 8B). Reuse for all samples before releasing the buffer.
module har_npu_core (
    input logic clk,rst_ni,start,ack_done,batch_two,abort_i,
    input logic [511:0] input_features,input_features1,
    input logic [1023:0] bias1,
    input logic [191:0] bias2,
    input logic [15:0] requant_mult,
    input logic [4:0] requant_shift,
    input logic tile_valid_i,
    input logic [511:0] tile_data_i,
    input logic dma_read_i,dma_write_i,
    output wire layer_o,
    output logic [4:0] tile_index_o,
    output wire tile_consumed_o,
    output logic busy,done,
    output wire [255:0] hidden,hidden1,
    output wire [191:0] scores,scores1,
    output logic [2:0] class_id,class_id1,
    output logic [31:0] cycle_count,overlap_count,fc1_cycles,fc2_cycles,
    output logic [31:0] read_overlap_count,write_overlap_count
);
    localparam [2:0] IDLE=0,WAIT_TILE=1,ISSUE=2,DRAIN=3,QUANT=4,FINISH=5;
    logic [2:0] state;
    logic layer,two,sample;
    wire product_valid,product_sample;
    logic [4:0] quant_index;
    logic quant_sample;
    logic signed [15:0] p1[0:31][0:1],p2[0:5];
    logic signed [31:0] a1[0:1][0:31],a2[0:1][0:5];
    logic [255:0] h[0:1];
    wire issue=state==ISSUE;
    wire [511:0] x=sample ? input_features1:input_features;
    wire [255:0] hs=h[sample];
    assign layer_o=layer;
    assign tile_consumed_o=state==DRAIN;
    assign product_valid=issue;
    assign product_sample=sample;
    assign hidden=h[0]; assign hidden1=h[1];
    genvar k;
    generate for(k=0;k<6;k=k+1) begin: score_outputs
        assign scores[k*32+:32]=a2[0][k];
        assign scores1[k*32+:32]=a2[1][k];
    end endgenerate
    // One shared requantizer; INT8 operands, INT32 accumulators/bias/scores.
    function automatic [7:0] quant(input logic signed [31:0] v);
        logic [47:0] scaled;
        begin
            scaled=0;
            if(v>0) begin
                scaled=$unsigned(v)*requant_mult;
                if(requant_shift!=0)
                    scaled=(scaled+(48'd1<<(requant_shift-1)))>>requant_shift;
            end
            quant=scaled>127 ? 8'd127:scaled[7:0];
        end
    endfunction
    function automatic [2:0] argmax(input logic [191:0] v);
        logic signed [31:0] best; integer j;
        begin
            best=$signed(v[31:0]);argmax=0;
            for(j=1;j<6;j=j+1)
                if($signed(v[j*32+:32])>best) begin best=$signed(v[j*32+:32]);argmax=3'(j);end
        end
    endfunction
    integer o,s;
    // Multiply and accumulate in one cycle. Keep INT8 operands and INT32
    // accumulation; remove the 1120-bit product pipeline rather than MACs.
    // The clock period is verified by real synthesis and post-route STA.
    genvar j;
    generate for(j=0;j<32;j=j+1) begin: fc1_products
        assign p1[j][0]=$signed(x[tile_index_o*16+:8])*$signed(tile_data_i[j*16+:8]);
        assign p1[j][1]=$signed(x[tile_index_o*16+8+:8])*$signed(tile_data_i[j*16+8+:8]);
    end
    for(j=0;j<6;j=j+1) begin: fc2_products
        assign p2[j]=$signed(hs[tile_index_o*8+:8])*$signed(tile_data_i[j*8+:8]);
    end endgenerate
    always_ff @(posedge clk or negedge rst_ni) begin
        if(!rst_ni) begin
            state<=IDLE;busy<=0;done<=0;layer<=0;two<=0;sample<=0;
            tile_index_o<=0;
            quant_index<=0;quant_sample<=0;h[0]<=0;h[1]<=0;
            class_id<=0;class_id1<=0;cycle_count<=0;overlap_count<=0;
            read_overlap_count<=0;write_overlap_count<=0;fc1_cycles<=0;fc2_cycles<=0;
            for(s=0;s<2;s=s+1) begin
                for(o=0;o<32;o=o+1) a1[s][o]<=0;
                for(o=0;o<6;o=o+1) a2[s][o]<=0;
            end
        end else begin
            if(busy) cycle_count<=cycle_count+1'b1;
            if(product_valid) begin
                if(dma_read_i || dma_write_i) overlap_count<=overlap_count+1'b1;
                if(dma_read_i) read_overlap_count<=read_overlap_count+1'b1;
                if(dma_write_i) write_overlap_count<=write_overlap_count+1'b1;
                if(!layer) begin
                    fc1_cycles<=fc1_cycles+1'b1;
                    for(o=0;o<32;o=o+1)
                        a1[product_sample][o] <= (tile_index_o==0 ? $signed(bias1[o*32+:32]):a1[product_sample][o])
                            + {{16{p1[o][0][15]}},p1[o][0]} + {{16{p1[o][1][15]}},p1[o][1]};
                end else begin
                    fc2_cycles<=fc2_cycles+1'b1;
                    for(o=0;o<6;o=o+1)
                        a2[product_sample][o] <= (tile_index_o==0 ? $signed(bias2[o*32+:32]):a2[product_sample][o])
                            + {{16{p2[o][15]}},p2[o]};
                end
            end
            case(state)
                IDLE:if(start) begin
                    busy<=1;done<=0;layer<=0;two<=batch_two;tile_index_o<=0;state<=WAIT_TILE;
                    cycle_count<=0;overlap_count<=0;read_overlap_count<=0;write_overlap_count<=0;
                    fc1_cycles<=0;fc2_cycles<=0;h[0]<=0;h[1]<=0;
                end else if(ack_done) done<=0;
                WAIT_TILE:if(tile_valid_i) begin sample<=0;state<=ISSUE;end
                ISSUE:if(!two || sample) state<=DRAIN;else sample<=1;
                DRAIN:if(tile_consumed_o) begin
                    if(tile_index_o!=31) begin tile_index_o<=tile_index_o+1'b1;state<=WAIT_TILE;end
                    else if(!layer) begin quant_index<=0;quant_sample<=0;state<=QUANT;end
                    else state<=FINISH;
                end
                QUANT:begin
                    h[quant_sample][quant_index*8+:8]<=quant(a1[quant_sample][quant_index]);
                    if(quant_index==31) begin
                        if(two && !quant_sample) begin quant_sample<=1;quant_index<=0;end
                        else begin layer<=1;tile_index_o<=0;state<=WAIT_TILE;end
                    end else quant_index<=quant_index+1'b1;
                end
                FINISH:begin class_id<=argmax(scores);class_id1<=argmax(scores1);busy<=0;done<=1;state<=IDLE;end
                default:state<=IDLE;
            endcase
            if(abort_i && busy) begin state<=IDLE;busy<=0;done<=1;end
        end
    end
endmodule
