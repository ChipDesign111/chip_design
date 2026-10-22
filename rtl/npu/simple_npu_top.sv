// MMIO configuration and autonomous SRAM weight-tile prefetch.
module simple_npu_top (
    input logic clka,rst_ni,ena,wea,dma_write_i,
    input logic [11:0] addra,
    input logic [31:0] dina,
    output wire busy_o,
    output logic [31:0] douta,
    output wire auto_start_o,
    output wire [31:0] auto_source_o,auto_dest_o,auto_words_o,
    input logic dma_busy_i,dma_done_i,dma_error_i,dma_read_i,dma_write_active_i
);
    logic [511:0] x0,x1;
    logic [1023:0] b1;
    logic [191:0] b2;
    logic [15:0] mult;
    logic [4:0] shift;
    logic batch_two,error;
    logic [31:0] w1_base,w2_base;
    wire busy,done,layer,consumed;
    wire [4:0] tile_index;
    wire [511:0] tile_data;
    wire [255:0] h0,h1;
    wire [191:0] scores0,scores1;
    wire [2:0] class0,class1;
    wire [31:0] cycles,overlap,fc1_cycles,fc2_cycles,read_overlap,write_overlap;
    logic layer_q,pending,loading_bank;
    logic [5:0] next_load;
    logic [1:0] ready;
    logic [15:0] received;
    logic [31:0] loads;
    wire write_req=ena && wea;
    wire cpu_write=write_req && !dma_write_i;
    wire [32:0] end1={1'b0,w1_base}+33'd2048,end2={1'b0,w2_base}+33'd256;
    wire valid_bases=w1_base[1:0]==0 && w2_base[1:0]==0 &&
        w1_base>=32'h80000000 && end1<=33'h080002000 &&
        w2_base>=32'h80000000 && end2<=33'h080002000;
    wire start=cpu_write && addra==0 && dina[0] && !busy && !dma_busy_i && valid_bases;
    wire tile_window=addra>=64 && addra<96;
    wire safe_tile_write=write_req && dma_write_i && tile_window && pending &&
        addra[4]==loading_bank && !ready[loading_bank];
    wire load_finished=pending && !dma_busy_i && dma_done_i;
    wire load_failed=load_finished && (dma_error_i || received!=(layer_q ? 16'h0003:16'hffff));
    assign busy_o=busy;
    assign auto_start_o=busy && layer==layer_q && !pending && !dma_busy_i && next_load<32 && !ready[next_load[0]];
    assign auto_source_o=layer ? w2_base+({26'd0,next_load}<<3):w1_base+({26'd0,next_load}<<6);
    assign auto_dest_o=32'h70000100+({31'd0,next_load[0]}<<6);
    assign auto_words_o=layer ? 32'd2:32'd16;
    har_weight_store weights(.clk(clka),.we_i(safe_tile_write),.bank_i(addra[4]),
        .word_i(addra[3:0]),.data_i(dina),.compute_bank_i(tile_index[0]),.tile_o(tile_data));
    har_npu_core core(.clk(clka),.rst_ni(rst_ni),.start(start),
        .ack_done(cpu_write && addra==0 && dina[1]),.batch_two(batch_two),.abort_i(load_failed),
        .input_features(x0),.input_features1(x1),.bias1(b1),.bias2(b2),
        .requant_mult(mult),.requant_shift(shift),
        // With a pending prefetch, issue the short MAC burst as streaming
        // writes begin. Otherwise the 1/2-sample burst ends before the AXI
        // crossbar delivers any data, providing no useful transfer overlap.
        .tile_valid_i(ready[tile_index[0]] && layer==layer_q && !auto_start_o &&
                      (!pending || dma_write_active_i)),.tile_data_i(tile_data),
        .layer_o(layer),.tile_index_o(tile_index),.tile_consumed_o(consumed),
        .dma_read_i(dma_read_i),.dma_write_i(dma_write_active_i),.busy(busy),.done(done),
        .hidden(h0),.hidden1(h1),.scores(scores0),.scores1(scores1),.class_id(class0),.class_id1(class1),
        .cycle_count(cycles),.overlap_count(overlap),.fc1_cycles(fc1_cycles),.fc2_cycles(fc2_cycles),
        .read_overlap_count(read_overlap),.write_overlap_count(write_overlap));
    always_ff @(posedge clka or negedge rst_ni) begin
        if(!rst_ni) begin
            x0<=0;x1<=0;b1<=0;b2<=0;mult<=1;shift<=0;batch_two<=0;
            w1_base<=0;w2_base<=0;error<=0;douta<=0;ready<=0;
            layer_q<=0;pending<=0;loading_bank<=0;next_load<=0;received<=0;loads<=0;
        end else begin
            douta<=0;
            if(start) begin ready<=0;next_load<=0;layer_q<=0;pending<=0;error<=0;loads<=0;end
            if(layer!=layer_q) begin layer_q<=layer;ready<=0;next_load<=0;received<=0;end
            if(auto_start_o) begin
                pending<=1;loading_bank<=next_load[0];next_load<=next_load+1'b1;received<=0;
            end
            if(safe_tile_write) received[addra[3:0]]<=1;
            if(consumed) ready[tile_index[0]]<=0;
            if(load_finished) begin
                pending<=0;
                if(load_failed) error<=1;
                else begin ready[loading_bank]<=1;loads<=loads+1'b1;end
            end
            if(write_req && dma_write_i && !safe_tile_write) error<=1;
            if(cpu_write) begin
                if(busy || dma_busy_i) error<=1;
                else case(addra)
                    0:if(dina[0]) begin if(!valid_bases) error<=1;end else if(dina[1]) error<=0;
                    4:if(dina[31:16]==0) mult<=dina[15:0];else error<=1;
                    5:if(dina<=31) shift<=dina[4:0];else error<=1;
                    6:if(dina==1 || dina==2) batch_two<=dina==2;else error<=1;
                    8:w1_base<=dina;
                    9:w2_base<=dina;
                    default:begin
                        if(addra>=16 && addra<32) x0[(addra-16)*32+:32]<=dina;
                        else if(addra>=624 && addra<656) b1[(addra-624)*32+:32]<=dina;
                        else if(addra>=656 && addra<662) b2[(addra-656)*32+:32]<=dina;
                        else if(addra>=768 && addra<784) x1[(addra-768)*32+:32]<=dina;
                        else error<=1;
                    end
                endcase
            end
            if(ena && !wea) case(addra)
                1:douta<={29'b0,error,busy,done};
                2:douta<={29'b0,class0};
                3:douta<=cycles;
                4:douta<={16'b0,mult};
                5:douta<={27'b0,shift};
                6:douta<=batch_two ? 2:1;
                7:douta<=overlap;
                8:douta<=w1_base;
                9:douta<=w2_base;
                10:douta<=fc1_cycles;
                11:douta<=fc2_cycles;
                12:douta<=loads;
                13:douta<=read_overlap;
                14:douta<=write_overlap;
                806:douta<={29'b0,class1};
                default:begin
                    if(addra>=672 && addra<680) douta<=h0[(addra-672)*32+:32];
                    else if(addra>=704 && addra<710) douta<=scores0[(addra-704)*32+:32];
                    else if(addra>=784 && addra<792) douta<=h1[(addra-784)*32+:32];
                    else if(addra>=800 && addra<806) douta<=scores1[(addra-800)*32+:32];
                end
            endcase
        end
    end
endmodule
