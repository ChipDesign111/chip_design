// INT8 64->32->6 with up to eight register-resident samples.
// Each weight tile is reused for every sample before it is released.
module har_npu_core (
    input logic clk,rst_ni,start,ack_done,
    input logic [3:0] batch_count,
    input logic abort_i,
    input logic [4095:0] input_features,
    input logic [1023:0] bias1,
    input logic [191:0] bias2,
    input logic [15:0] requant_mult,
    input logic [4:0] requant_shift,
    input logic tile_valid_i,tile_next_valid_i,
    input logic [511:0] tile_data_i,
    input logic dma_read_i,dma_write_i,
    output wire layer_o,
    output logic [4:0] tile_index_o,
    output wire tile_consumed_o,
    output logic busy,done,
    output wire [2047:0] hidden_all,
    output wire [1535:0] scores_all,
    output wire [23:0] class_all,
    output logic [31:0] cycle_count,overlap_count,fc1_cycles,fc2_cycles,
    output logic [31:0] read_overlap_count,write_overlap_count
);
    localparam [2:0] IDLE=0,WAIT_TILE=1,ISSUE=2,QUANT=3,FINISH=4,TAIL=5;
    localparam int MAX_BATCH=8;
    logic [2:0] state;
    logic layer;
    logic [3:0] batch_q;
    logic [2:0] sample,quant_sample;
    wire product_valid,product_first;
    wire [2:0] product_sample;
    logic signed [15:0] p1[0:31][0:1],p2[0:5];
    logic signed [15:0] p1_q[0:31][0:1],p2_q[0:5];
    logic pipeline_valid_q,pipeline_first_q;
    logic [2:0] pipeline_sample_q;
    logic signed [31:0] a1[0:7][0:31],a2[0:7][0:5];
    logic [255:0] h[0:7];
    logic [2:0] class_id_q[0:7];
    wire issue=state==ISSUE;
    wire last_sample_issue=issue && sample==batch_q[2:0]-1'b1;
    wire [511:0] x=input_features[sample*512+:512];
    wire [255:0] hs=h[sample];
    assign layer_o=layer;
    // Release the current bank on its final use, then either hand off to an
    // already-ready bank without a bubble or wait only for a real prefetch.
    assign tile_consumed_o=last_sample_issue;
    assign product_valid=issue;
    assign product_first=tile_index_o==0;
    assign product_sample=sample;

    genvar gs,go;
    generate
        for(gs=0;gs<MAX_BATCH;gs=gs+1) begin: output_views
            assign hidden_all[gs*256+:256]=h[gs];
            assign class_all[gs*3+:3]=class_id_q[gs];
            for(go=0;go<6;go=go+1) begin: score_views
                assign scores_all[gs*192+go*32+:32]=a2[gs][go];
            end
        end
    endgenerate

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
        logic signed [31:0] best;
        integer j;
        begin
            best=$signed(v[31:0]);
            argmax=0;
            for(j=1;j<6;j=j+1)
                if($signed(v[j*32+:32])>best) begin
                    best=$signed(v[j*32+:32]);
                    argmax=3'(j);
                end
        end
    endfunction

    wire [191:0] class_scores[0:7];
    wire [2:0] class_candidate[0:7];
    generate
        for(gs=0;gs<MAX_BATCH;gs=gs+1) begin: class_calc
            for(go=0;go<6;go=go+1) begin: score_pack
                assign class_scores[gs][go*32+:32]=a2[gs][go];
            end
            assign class_candidate[gs]=argmax(class_scores[gs]);
        end
    endgenerate

    integer o,s;
    genvar j;
    // Register INT8 products in ISSUE and accumulate them in the next cycle.
    generate
        for(j=0;j<32;j=j+1) begin: fc1_products
            assign p1[j][0]=$signed(x[tile_index_o*16+:8])*$signed(tile_data_i[j*16+:8]);
            assign p1[j][1]=$signed(x[tile_index_o*16+8+:8])*$signed(tile_data_i[j*16+8+:8]);
        end
        for(j=0;j<6;j=j+1) begin: fc2_products
            assign p2[j]=$signed(hs[tile_index_o*8+:8])*$signed(tile_data_i[j*8+:8]);
        end
    endgenerate

    always_ff @(posedge clk or negedge rst_ni) begin
        if(!rst_ni) begin
            state<=IDLE;
            busy<=0;
            done<=0;
            layer<=0;
            batch_q<=1;
            sample<=0;
            pipeline_valid_q<=0;
            pipeline_sample_q<=0;
            pipeline_first_q<=0;
            tile_index_o<=0;
            quant_sample<=0;
            class_id_q[0]<=0;class_id_q[1]<=0;class_id_q[2]<=0;class_id_q[3]<=0;
            class_id_q[4]<=0;class_id_q[5]<=0;class_id_q[6]<=0;class_id_q[7]<=0;
            cycle_count<=0;
            overlap_count<=0;
            read_overlap_count<=0;
            write_overlap_count<=0;
            fc1_cycles<=0;
            fc2_cycles<=0;
            for(s=0;s<MAX_BATCH;s=s+1) begin
                h[s]<=0;
                for(o=0;o<32;o=o+1) a1[s][o]<=0;
                for(o=0;o<6;o=o+1) a2[s][o]<=0;
            end
        end else begin
            if(busy) cycle_count<=cycle_count+1'b1;
            if(product_valid) begin
                if(dma_read_i || dma_write_i) overlap_count<=overlap_count+1'b1;
                if(dma_read_i) read_overlap_count<=read_overlap_count+1'b1;
                if(dma_write_i) write_overlap_count<=write_overlap_count+1'b1;
                if(!layer) fc1_cycles<=fc1_cycles+1'b1;
                else fc2_cycles<=fc2_cycles+1'b1;
            end
            if(issue) begin
                pipeline_valid_q<=1;
                pipeline_sample_q<=sample;
                pipeline_first_q<=product_first;
                for(o=0;o<32;o=o+1) begin
                    p1_q[o][0]<=p1[o][0];
                    p1_q[o][1]<=p1[o][1];
                end
                for(o=0;o<6;o=o+1) p2_q[o]<=p2[o];
            end else begin
                pipeline_valid_q<=0;
            end
            if(pipeline_valid_q) begin
                if(!layer) begin
                    for(o=0;o<32;o=o+1)
                        a1[pipeline_sample_q][o] <=
                            (pipeline_first_q ? $signed(bias1[o*32+:32]):a1[pipeline_sample_q][o])
                            + {{16{p1_q[o][0][15]}},p1_q[o][0]}
                            + {{16{p1_q[o][1][15]}},p1_q[o][1]};
                end else begin
                    for(o=0;o<6;o=o+1)
                        a2[pipeline_sample_q][o] <=
                            (pipeline_first_q ? $signed(bias2[o*32+:32]):a2[pipeline_sample_q][o])
                            + {{16{p2_q[o][15]}},p2_q[o]};
                end
            end
            case(state)
                IDLE:if(start) begin
                    busy<=1;
                    done<=0;
                    layer<=0;
                    batch_q<=batch_count;
                    sample<=0;
                    pipeline_valid_q<=0;
                    tile_index_o<=0;
                    state<=WAIT_TILE;
                    cycle_count<=0;
                    overlap_count<=0;
                    read_overlap_count<=0;
                    write_overlap_count<=0;
                    fc1_cycles<=0;
                    fc2_cycles<=0;
                    class_id_q[0]<=0;class_id_q[1]<=0;class_id_q[2]<=0;class_id_q[3]<=0;
                    class_id_q[4]<=0;class_id_q[5]<=0;class_id_q[6]<=0;class_id_q[7]<=0;
                    for(s=0;s<MAX_BATCH;s=s+1) h[s]<=0;
                end else if(ack_done) done<=0;
                WAIT_TILE:if(tile_valid_i) begin
                    sample<=0;
                    state<=ISSUE;
                end
                ISSUE:if(last_sample_issue) begin
                    if(tile_index_o==31) begin
                        if(!layer) begin
                            quant_sample<=0;
                            tile_index_o<=0;
                        end
                        state<=TAIL;
                    end else begin
                        tile_index_o<=tile_index_o+1'b1;
                        sample<=0;
                        state<=tile_next_valid_i ? ISSUE:WAIT_TILE;
                    end
                end else sample<=sample+1'b1;
                TAIL:state<=layer ? FINISH:QUANT;
                QUANT:begin
                    h[quant_sample][tile_index_o*8+:8]<=quant(a1[quant_sample][tile_index_o]);
                    if(tile_index_o==31) begin
                        if(quant_sample!=batch_q[2:0]-1'b1) begin
                            quant_sample<=quant_sample+1'b1;
                            tile_index_o<=0;
                        end else begin
                            layer<=1;
                            tile_index_o<=0;
                            state<=WAIT_TILE;
                        end
                    end else begin
                        tile_index_o<=tile_index_o+1'b1;
                    end
                end
                FINISH:begin
                    class_id_q[0]<=class_candidate[0];class_id_q[1]<=class_candidate[1];
                    class_id_q[2]<=class_candidate[2];class_id_q[3]<=class_candidate[3];
                    class_id_q[4]<=class_candidate[4];class_id_q[5]<=class_candidate[5];
                    class_id_q[6]<=class_candidate[6];class_id_q[7]<=class_candidate[7];
                    busy<=0;
                    done<=1;
                    state<=IDLE;
                end
                default:state<=IDLE;
            endcase
            if(abort_i && busy) begin
                state<=IDLE;
                busy<=0;
                done<=1;
            end
        end
    end
endmodule
