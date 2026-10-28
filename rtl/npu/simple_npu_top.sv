// MMIO configuration and autonomous SRAM weight prefetch.
// Supports register-resident batches of up to eight samples without NPU SRAM.
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
    localparam int INPUT2_BASE=1024;
    localparam int OUTPUT2_BASE=1152;
    logic [511:0] x[0:3];
    logic [1023:0] b1;
    logic [191:0] b2;
    logic [15:0] mult;
    logic [4:0] shift;
    logic [3:0] batch_count;
    logic error;
    logic [31:0] w1_base,w2_base;
    wire busy,done,layer,consumed;
    wire [4:0] tile_index;
    wire [511:0] tile_data;
    wire [2047:0] hidden_all;
    wire [1535:0] scores_all;
    wire [23:0] class_all;
    wire [31:0] cycles,overlap,fc1_cycles,fc2_cycles,read_overlap,write_overlap;
    logic layer_q,pending,pending_w2,loading_bank;
    logic [5:0] next_w1;
    logic [2:0] next_w2;
    logic [1:0] ready_w1,ready_w2;
    logic [15:0] received;
    logic [31:0] loads;
    integer input_rel,input_slot,input_word,out_rel,out_slot,out_word;
    wire [4095:0] input_packed={2048'd0,x[3],x[2],x[1],x[0]};
    wire write_req=ena && wea;
    wire cpu_write=write_req && !dma_write_i;
    wire [32:0] end1={1'b0,w1_base}+33'd2048,end2={1'b0,w2_base}+33'd256;
    wire valid_bases=w1_base[1:0]==0 && w2_base[1:0]==0 &&
        w1_base>=32'h80000000 && end1<=33'h080002000 &&
        w2_base>=32'h80000000 && end2<=33'h080002000;
    wire start=cpu_write && addra==0 && dina[0] && !busy && !dma_busy_i && valid_bases;
    wire tile_window=addra>=64 && addra<96;
    wire want_w1=next_w1<32;
    wire load_bank=want_w1 ? next_w1[0]:next_w2[0];
    wire load_pending=want_w1 || next_w2<4;
    wire load_bank_free=!ready_w1[load_bank] && !ready_w2[load_bank];
    wire safe_tile_write=write_req && dma_write_i && tile_window && pending &&
        addra[4]==loading_bank && !ready_w1[loading_bank] && !ready_w2[loading_bank];
    wire load_finished=pending && !dma_busy_i && dma_done_i;
    wire load_failed=load_finished &&
        (dma_error_i || received!=(pending_w2 ? 16'h0fff:16'hffff));
    wire [4:0] next_tile_index=tile_index+1'b1;
    wire compute_bank=layer ? tile_index[3]:tile_index[0];
    wire next_bank=layer ? next_tile_index[3]:next_tile_index[0];
    wire current_ready=layer ? ready_w2[compute_bank]:ready_w1[compute_bank];
    wire next_ready=layer ? ready_w2[next_bank]:ready_w1[next_bank];
    wire bank_published=|{ready_w1,ready_w2};
    wire next_tile_valid=next_ready && layer==layer_q && !auto_start_o &&
        (!pending || dma_write_active_i);
    assign busy_o=busy;
    assign auto_start_o=busy && !pending && !dma_busy_i && load_pending && load_bank_free;
    assign auto_source_o=want_w1 ?
        w1_base+({26'd0,next_w1}<<6):w2_base+({26'd0,next_w2}*32'd48);
    assign auto_dest_o=32'h70000100+({31'd0,load_bank}<<6);
    assign auto_words_o=want_w1 ? 32'd16:32'd12;
    har_weight_store weights(.clk(clka),.we_i(safe_tile_write),.bank_i(addra[4]),
        .word_i(addra[3:0]),.data_i(dina),.compute_bank_i(compute_bank),
        .packed_i(layer),.tile_index_i(tile_index),.tile_o(tile_data));
    har_npu_core core(.clk(clka),.rst_ni(rst_ni),.start(start),
        .ack_done(cpu_write && addra==0 && dina[1]),.batch_count(batch_count),.abort_i(load_failed),
        .input_features(input_packed),.bias1(b1),.bias2(b2),
        .requant_mult(mult),.requant_shift(shift),
        .tile_valid_i(current_ready && layer==layer_q && !auto_start_o &&
                      (!pending || dma_write_active_i)),.tile_next_valid_i(next_tile_valid),
        .tile_data_i(tile_data),
        .layer_o(layer),.tile_index_o(tile_index),.tile_consumed_o(consumed),
        .dma_read_i(dma_read_i),.dma_write_i(dma_write_active_i),.busy(busy),.done(done),
        .hidden_all(hidden_all),.scores_all(scores_all),.class_all(class_all),
        .cycle_count(cycles),.overlap_count(overlap),.fc1_cycles(fc1_cycles),.fc2_cycles(fc2_cycles),
        .read_overlap_count(read_overlap),.write_overlap_count(write_overlap));
    always_ff @(posedge clka or negedge rst_ni) begin
        if(!rst_ni) begin
            for(input_slot=0;input_slot<4;input_slot=input_slot+1) x[input_slot]<=0;
            b1<=0;b2<=0;mult<=1;shift<=0;batch_count<=1;
            w1_base<=0;w2_base<=0;error<=0;douta<=0;ready_w1<=0;ready_w2<=0;
            layer_q<=0;pending<=0;pending_w2<=0;loading_bank<=0;
            next_w1<=0;next_w2<=0;received<=0;loads<=0;
        end else begin
            douta<=0;
            if(start) begin
                ready_w1<=0;ready_w2<=0;next_w1<=0;next_w2<=0;layer_q<=0;
                pending<=0;pending_w2<=0;error<=0;loads<=0;
            end
            if(layer!=layer_q) begin layer_q<=layer;ready_w1<=0;end
            if(auto_start_o) begin
                pending<=1;pending_w2<=!want_w1;
                loading_bank<=load_bank;received<=0;
                if(want_w1) next_w1<=next_w1+1'b1;
                else next_w2<=next_w2+1'b1;
            end
            if(safe_tile_write) received[addra[3:0]]<=1;
            if(consumed) begin
                if(!layer) ready_w1[compute_bank]<=0;
                else if(tile_index[2:0]==3'd7) ready_w2[compute_bank]<=0;
            end
            if(load_finished) begin
                pending<=0;
                if(load_failed) error<=1;
                else begin
                    if(pending_w2) begin ready_w2[loading_bank]<=1;loads<=loads+32'd8;end
                    else begin ready_w1[loading_bank]<=1;loads<=loads+1'b1;end
                end
            end
            if(write_req && dma_write_i && !safe_tile_write) error<=1;
            if(cpu_write) begin
                if(busy || dma_busy_i) error<=1;
                else case(addra)
                    0:if(dina[0]) begin if(!valid_bases) error<=1;end else if(dina[1]) error<=0;
                    4:if(dina[31:16]==0) mult<=dina[15:0];else error<=1;
                    5:if(dina<=31) shift<=dina[4:0];else error<=1;
                    6:if(dina>=1 && dina<=4) batch_count<=dina[3:0];else error<=1;
                    8:w1_base<=dina;
                    9:w2_base<=dina;
                    default:begin
                        if(addra>=16 && addra<32) x[0][(addra-16)*32+:32]<=dina;
                        else if(addra>=624 && addra<656) b1[(addra-624)*32+:32]<=dina;
                        else if(addra>=656 && addra<662) b2[(addra-656)*32+:32]<=dina;
                        else if(addra>=768 && addra<784) x[1][(addra-768)*32+:32]<=dina;
                        else if(addra>=INPUT2_BASE && addra<INPUT2_BASE+64) begin
                            input_rel=addra-INPUT2_BASE;
                            input_slot=2+(input_rel>>4);
                            input_word=input_rel & 15;
                            x[input_slot][input_word*32+:32]<=dina;
                        end else error<=1;
                    end
                endcase
            end
            if(ena && !wea) case(addra)
                1:douta<={29'b0,error,busy,done};
                2:douta<={29'b0,class_all[2:0]};
                3:douta<=cycles;
                4:douta<={16'b0,mult};
                5:douta<={27'b0,shift};
                6:douta<={28'b0,batch_count};
                7:douta<=overlap;
                8:douta<=w1_base;
                9:douta<=w2_base;
                10:douta<=fc1_cycles;
                11:douta<=fc2_cycles;
                12:douta<=loads;
                13:douta<=read_overlap;
                14:douta<=write_overlap;
                806:douta<={29'b0,class_all[3+:3]};
                default:begin
                    if(addra>=672 && addra<680) douta<=hidden_all[(addra-672)*32+:32];
                    else if(addra>=704 && addra<710) douta<=scores_all[(addra-704)*32+:32];
                    else if(addra>=784 && addra<792)
                        douta<=hidden_all[256+(addra-784)*32+:32];
                    else if(addra>=800 && addra<806)
                        douta<=scores_all[192+(addra-800)*32+:32];
                    else if(addra>=OUTPUT2_BASE && addra<OUTPUT2_BASE+96) begin
                        out_rel=addra-OUTPUT2_BASE;
                        out_slot=2+(out_rel>>4);
                        out_word=out_rel & 15;
                        if(out_word<8)
                            douta<=hidden_all[out_slot*256+out_word*32+:32];
                        else if(out_word<14)
                            douta<=scores_all[out_slot*192+(out_word-8)*32+:32];
                        else if(out_word==14)
                            douta<={29'b0,class_all[out_slot*3+:3]};
                        else douta<=0;
                    end else douta<=0;
                end
            endcase
        end
    end
endmodule
