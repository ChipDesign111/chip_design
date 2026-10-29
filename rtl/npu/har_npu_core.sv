// INT8 64->32->6 with up to four register-resident samples.
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
    localparam [2:0] IDLE=0,WAIT_TILE=1,ISSUE=2,QUANT=3,FINISH=4;
    localparam int MAX_BATCH=4;
    localparam int FC1_TILES=32;
    localparam int FC2_GROUPS=4;
    logic [2:0] state;
    logic layer;
    logic [3:0] batch_q;
    logic [2:0] sample,quant_sample,finish_sample;
    wire product_valid,product_first;
    wire [2:0] product_sample;
    // FC1 maps these 64 multipliers as 32 outputs by 2 lanes. FC2 remaps the
    // first 48 to 8 input positions by 6 outputs. The multiplier bank is
    // physically shared; only operand routing changes between layers.
    logic signed [15:0] product[0:63];
    logic signed [31:0] a1[0:MAX_BATCH-1][0:31],a2[0:MAX_BATCH-1][0:5];
    logic [255:0] h[0:MAX_BATCH-1];
    logic [2:0] class_id_q[0:MAX_BATCH-1];
    wire issue=state==ISSUE;
    wire last_sample_issue=issue && sample==batch_q[2:0]-1'b1;
    wire [511:0] x=input_features[sample*512+:512];
    wire [255:0] hs=h[sample];
    wire [1:0] fc2_group=tile_index_o[1:0];
    assign layer_o=layer;
    // Release the current bank on its final use, then either hand off to an
    // already-ready bank without a bubble or wait only for a real prefetch.
    assign tile_consumed_o=last_sample_issue;
    assign product_valid=issue;
    assign product_first=tile_index_o==0;
    assign product_sample=sample;

    genvar gs,go;
    generate
        for(gs=0;gs<8;gs=gs+1) begin: output_views
            if(gs<MAX_BATCH) begin: active_output
                assign hidden_all[gs*256+:256]=h[gs];
                assign class_all[gs*3+:3]=class_id_q[gs];
                for(go=0;go<6;go=go+1) begin: score_views
                    assign scores_all[gs*192+go*32+:32]=a2[gs][go];
                end
            end else begin: zero_output
                assign hidden_all[gs*256+:256]='0;
                assign class_all[gs*3+:3]='0;
                for(go=0;go<6;go=go+1) begin: score_views
                    assign scores_all[gs*192+go*32+:32]='0;
                end
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

    logic [191:0] finish_scores;
    integer finish_o;
    always_comb begin
        finish_scores='0;
        for(finish_o=0;finish_o<6;finish_o=finish_o+1)
            finish_scores[finish_o*32+:32]=a2[finish_sample][finish_o];
    end
    wire [2:0] finish_class=argmax(finish_scores);

    integer o,s;
    genvar j,k;
    // One shared multiplier bank. FC2 packet weights are stored contiguous as
    // eight six-byte rows, so flat product index p maps to row p/6 and output
    // p%6. This uses 48 of the 64 lanes and keeps FC1 unchanged.
    generate
        for(j=0;j<32;j=j+1) begin: fc1_products
            for(k=0;k<2;k=k+1) begin: lanes
                localparam int P=j*2+k;
                if(P<48) begin: shared
                    localparam int W2_ROW=P/6;
                    assign product[P]=layer ?
                        $signed(hs[(fc2_group*8+W2_ROW)*8+:8])*
                            $signed(tile_data_i[P*8+:8]) :
                        $signed(x[tile_index_o*16+k*8+:8])*
                            $signed(tile_data_i[j*16+k*8+:8]);
                end else begin: fc1_only
                    assign product[P]=
                        $signed(x[tile_index_o*16+k*8+:8])*
                            $signed(tile_data_i[j*16+k*8+:8]);
                end
            end
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
            finish_sample<=0;
            tile_index_o<=0;
            quant_sample<=0;
            class_id_q[0]<=0;class_id_q[1]<=0;class_id_q[2]<=0;class_id_q[3]<=0;
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
                if(!layer) begin
                    fc1_cycles<=fc1_cycles+1'b1;
                    for(o=0;o<32;o=o+1)
                        a1[product_sample][o] <=
                            (product_first ? $signed(bias1[o*32+:32]):a1[product_sample][o])
                            + {{16{product[o*2][15]}},product[o*2]}
                            + {{16{product[o*2+1][15]}},product[o*2+1]};
                end else begin
                    fc2_cycles<=fc2_cycles+1'b1;
                    for(o=0;o<6;o=o+1)
                        a2[product_sample][o] <=
                            (product_first ? $signed(bias2[o*32+:32]):a2[product_sample][o])
                            + {{16{product[o][15]}},product[o]}
                            + {{16{product[6+o][15]}},product[6+o]}
                            + {{16{product[12+o][15]}},product[12+o]}
                            + {{16{product[18+o][15]}},product[18+o]}
                            + {{16{product[24+o][15]}},product[24+o]}
                            + {{16{product[30+o][15]}},product[30+o]}
                            + {{16{product[36+o][15]}},product[36+o]}
                            + {{16{product[42+o][15]}},product[42+o]};
                end
            end
            case(state)
                IDLE:if(start) begin
                    busy<=1;
                    done<=0;
                    layer<=0;
                    batch_q<=batch_count;
                    sample<=0;
                    finish_sample<=0;
                    tile_index_o<=0;
                    state<=WAIT_TILE;
                    cycle_count<=0;
                    overlap_count<=0;
                    read_overlap_count<=0;
                    write_overlap_count<=0;
                    fc1_cycles<=0;
                    fc2_cycles<=0;
                    class_id_q[0]<=0;class_id_q[1]<=0;class_id_q[2]<=0;class_id_q[3]<=0;
                    for(s=0;s<MAX_BATCH;s=s+1) h[s]<=0;
                end else if(ack_done) done<=0;
                WAIT_TILE:if(tile_valid_i) begin
                    sample<=0;
                    state<=ISSUE;
                end
                ISSUE:if(last_sample_issue) begin
                    if(tile_index_o==FC1_TILES-1 && !layer) begin
                        quant_sample<=0;
                        tile_index_o<=0;
                        state<=QUANT;
                    end else if(layer && tile_index_o==FC2_GROUPS-1) begin
                        finish_sample<=0;
                        state<=FINISH;
                    end else begin
                        tile_index_o<=tile_index_o+1'b1;
                        sample<=0;
                        state<=tile_next_valid_i ? ISSUE:WAIT_TILE;
                    end
                end else sample<=sample+1'b1;
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
                    class_id_q[finish_sample]<=finish_class;
                    if(finish_sample==batch_q[1:0]-1'b1) begin
                        busy<=0;
                        done<=1;
                        state<=IDLE;
                    end else begin
                        finish_sample<=finish_sample+1'b1;
                    end
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
