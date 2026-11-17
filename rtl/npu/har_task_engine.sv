// Task ABI v1. Serial control shares the legacy MMIO/result mux and DMA.
// No bus request is cancelled: faults drain the current DMA before invalidation.
module har_task_engine (
    input logic clk_i,rst_ni,
    input logic reg_req_i,reg_we_i,
    input logic [5:0] reg_addr_i,
    input logic [31:0] reg_data_i,
    output logic [31:0] reg_data_o,
    input logic reject_i,legacy_start_i,
    input logic core_busy_i,core_done_i,core_error_i,
    input logic [31:0] core_data_i,
    output logic core_req_o,core_we_o,
    output logic [11:0] core_addr_o,
    output logic [31:0] core_data_o,
    output wire core_abort_o,core_invalidate_o,
    output wire post_write_o,
    output wire [6:0] post_index_o,
    output wire [7:0] post_data_o,
    input logic dma_busy_i,dma_done_i,dma_error_i,
    input logic ingress_i,
    input logic [31:0] ingress_addr_i,ingress_data_i,
    output wire ingress_core_o,
    output wire dma_start_o,
    output wire [31:0] dma_source_o,dma_dest_o,dma_words_o,
    output wire [3:0] dma_last_be_o,
    output wire busy_o,output_valid_o
);
    localparam [4:0] IDLE=0,FETCH=1,WAIT_DESC=2,CHECK=3,
        INPUT=4,WAIT_INPUT=5,BIAS=6,WAIT_BIAS=7,
        FWD_READ=8,FWD_WRITE=9,CONFIG=10,START_FC=11,WAIT_FC=12,
        POST_READ=13,POST_VALUE=14,FC_SCALE=15,ACT_PREP=16,ACT_SCALE=17,
        LUT=18,WAIT_LUT=19,STORE=20,OUTPUT=21,WAIT_OUTPUT=22,
        COMMIT=23,DRAIN=24;
    localparam [3:0] E_BUSY=1,E_ALIGN=2,E_RANGE=3,E_DESC=4,E_CONTEXT=5,
        E_DMA=6,E_VALUE=7,E_UNSUPPORTED=8;
    logic [4:0] state;
    logic [31:0] base_cfg,count_cfg,base_q;
    logic [7:0] count_q,index_q,completed_q;
    logic [31:0] cycles_q;
    logic done_q,failed_q,valid_q,rejected_q;
    logic [3:0] error_q,reject_q;
    logic [31:0] d[0:15];
    logic [15:0] received_q;
    logic [5:0] ingress_count_q;
    logic ingress_bad_q,bias_bad_q;
    logic [2:0] sample_q;
    logic [5:0] element_q;
    logic [3:0] word_q;
    logic [2:0] config_q;
    logic partial_q,forward_q;
    logic [31:0] partial_context_q;
    logic [5:0] partial_n_q,forward_n_q;
    logic [2:0] partial_batch_q,forward_batch_q;
    logic signed [7:0] quant_q,output_q;
    logic [31:0] lut_word_q;
    wire [3:0] op=d[0][11:8],activation=d[0][15:12];
    wire initialize=d[0][16],last_k=d[0][17],input_internal=d[0][18],keep=d[0][19];
    wire [6:0] k=d[1][6:0];
    wire [5:0] n=d[1][13:8];
    wire [2:0] batch=d[1][18:16];
    wire [15:0] input_stride=d[6][15:0],output_stride=d[6][31:16];
    wire [6:0] width=op==1 ? k:{1'b0,n};
    wire [4:0] input_words=({1'b0,width}+3)>>2;
    wire [3:0] output_words=({1'b0,n}+3)>>2;
    wire [31:0] input_bytes=(batch-1)*{16'd0,input_stride}+({27'd0,input_words}<<2);
    wire [31:0] output_bytes=(batch-1)*{16'd0,output_stride}+({28'd0,output_words}<<2);
    wire [31:0] weight_bytes=((({25'd0,k}+1)>>1)*(({26'd0,n}+7)>>3))<<4;
    wire [7:0] lut_index=quant_q[7:0]^8'h80;
    wire [31:0] input_row=d[2]+sample_q*{16'd0,input_stride};
    wire [31:0] output_row=d[5]+sample_q*{16'd0,output_stride};
    wire [31:0] input_mmio=sample_q==0 ? 32'h70000040 :
        sample_q==1 ? 32'h70000c00 : 32'h70001000+((sample_q-2)<<6);
    wire [31:0] packed_mmio=32'h70001680+({29'd0,sample_q}<<5);
    wire [31:0] desc_address=base_q+({24'd0,index_q}<<6);
    wire cpu_write=reg_req_i && reg_we_i;
    wire start=cpu_write && reg_addr_i==0 && reg_data_i==1;
    wire ack=cpu_write && reg_addr_i==0 && reg_data_i==2;
    assign busy_o=state!=IDLE;
    assign output_valid_o=valid_q;
    function automatic logic region(input logic [31:0] address,bytes);
        logic [32:0] ending;
        begin
            ending={1'b0,address}+{1'b0,bytes};
            region=bytes!=0 && address[1:0]==0 && address>=32'h80000000 && ending<=33'h080002000;
        end
    endfunction
    logic [3:0] descriptor_error;
    always_comb begin
        descriptor_error=0;
        if(d[0][7:0]!=1 || (op!=1 && op!=2) || activation>5 || d[0][21])
            descriptor_error=E_UNSUPPORTED;
        else if(d[0][31:22]!=0 || d[1][31:24]!=0 || d[8][31:24]!=0 ||
                d[12]>127 || d[14]!=0 || d[15]!=0 || d[0][20]!=(index_q==count_q-1))
            descriptor_error=E_DESC;
        else if(d[1][15:8]<1 || d[1][15:8]>32 || d[1][23:16]<1 || d[1][23:16]>4 ||
                (op==1 && (d[1][7:0]<1 || d[1][7:0]>64)) ||
                d[8][7:0]>24 || d[8][15:8]>24 || d[8][23:16]>24)
            descriptor_error=E_VALUE;
        else if((op==2 && (d[1][7:0]!=0 || d[3]!=0 || d[4]!=0 || initialize || !last_k || d[7]!=0 || d[8][7:0]!=0)) ||
                (op==1 && !initialize && d[4]!=0) ||
                (!last_k && (d[5]!=0 || output_stride!=0))) descriptor_error=E_DESC;
        else if(!last_k && (keep || d[0][20] || activation!=0)) descriptor_error=E_CONTEXT;
        else if((partial_q && (op!=1 || initialize || partial_context_q!=d[13] || partial_n_q!=n || partial_batch_q!=batch)) ||
                (!partial_q && op==1 && !initialize) ||
                (input_internal && (!forward_q || forward_n_q!=width || forward_batch_q!=batch)))
            descriptor_error=E_CONTEXT;
        else if(input_internal && (width>32 || d[2]!=0 || input_stride!=0)) descriptor_error=E_VALUE;
        else if(!input_internal && (input_stride<({27'd0,input_words}<<2) || input_stride[1:0]!=0))
            descriptor_error=E_VALUE;
        else if(last_k && keep && (d[5]!=0 || output_stride!=0)) descriptor_error=E_DESC;
        else if(last_k && !keep && (output_stride<({28'd0,output_words}<<2) || output_stride[1:0]!=0))
            descriptor_error=E_VALUE;
        else if((op==1 && d[3][1:0]!=0) || (op==1 && initialize && d[4][1:0]!=0) ||
                (!input_internal && d[2][1:0]!=0) || (last_k && !keep && d[5][1:0]!=0) ||
                (activation>=4 && d[11][1:0]!=0)) descriptor_error=E_ALIGN;
        else if((op==1 && !region(d[3],weight_bytes)) ||
                (op==1 && initialize && !region(d[4],{26'd0,n}<<2)) ||
                (!input_internal && !region(d[2],input_bytes)) ||
                (last_k && !keep && !region(d[5],output_bytes)) ||
                (activation>=4 && !region(d[11],256))) descriptor_error=E_RANGE;
        else if(activation<4 && d[11]!=0) descriptor_error=E_DESC;
        else if(last_k && !keep && !(({1'b0,d[5]}+{1'b0,output_bytes})<={1'b0,base_q} ||
                {1'b0,d[5]}>=({1'b0,base_q}+({25'd0,count_q}<<6)))) descriptor_error=E_RANGE;
    end
    assign dma_start_o=state==FETCH || state==INPUT || state==BIAS || state==LUT || state==OUTPUT;
    assign dma_source_o=state==FETCH ? desc_address : state==INPUT ? input_row :
        state==BIAS ? d[4] : state==LUT ? d[11]+{24'd0,lut_index[7:2],2'b00}:packed_mmio;
    assign dma_dest_o=state==FETCH ? 32'h70001640 : state==INPUT ? input_mmio :
        state==BIAS ? 32'h700009c0 : state==LUT ? 32'h70001700:output_row;
    assign dma_words_o=state==FETCH ? 32'd16 : state==INPUT ? {27'd0,input_words} :
        state==BIAS ? {26'd0,n} : state==LUT ? 32'd1:{28'd0,output_words};
    assign dma_last_be_o=state==OUTPUT && n[1:0]!=0 ? ((4'd1<<n[1:0])-1'b1):4'hf;
    wire input_ingress=state==WAIT_INPUT && ingress_addr_i>=input_mmio &&
        ingress_addr_i<input_mmio+({27'd0,input_words}<<2) && ingress_addr_i[1:0]==0;
    wire bias_ingress=state==WAIT_BIAS && ingress_addr_i>=32'h700009c0 &&
        ingress_addr_i<32'h700009c0+({26'd0,n}<<2) && ingress_addr_i[1:0]==0;
    wire desc_ingress=state==WAIT_DESC && ingress_addr_i>=32'h70001640 &&
        ingress_addr_i<32'h70001680 && ingress_addr_i[1:0]==0;
    wire lut_ingress=state==WAIT_LUT && ingress_addr_i==32'h70001700;
    wire tile_ingress=state==WAIT_FC && ingress_addr_i>=32'h70000100 && ingress_addr_i<32'h70000180;
    assign ingress_core_o=ingress_i && (input_ingress || bias_ingress);
    assign core_abort_o=state==DRAIN && !dma_busy_i;
    assign core_invalidate_o=(start && !busy_o && !core_busy_i && !dma_busy_i) || state==DRAIN ||
        (state==COMMIT && index_q==count_q-1);
    assign post_write_o=state==STORE;
    assign post_index_o={sample_q[1:0],element_q[4:0]};
    assign post_data_o=output_q;
    always_comb begin
        core_req_o=0;core_we_o=0;core_addr_o=0;core_data_o=0;
        case(state)
            FWD_READ:begin core_req_o=1;core_addr_o=(packed_mmio[13:2])+word_q;end
            FWD_WRITE:begin
                core_req_o=1;core_we_o=1;core_addr_o=input_mmio[13:2]+word_q;core_data_o=core_data_i;
            end
            CONFIG:begin
                core_req_o=1;core_we_o=1;
                case(config_q)
                    0:begin core_addr_o=0;core_data_o=2;end
                    1:begin core_addr_o=15;core_data_o=initialize ? 1:3;end
                    2:begin core_addr_o=32;core_data_o={25'd0,k};end
                    3:begin core_addr_o=33;core_data_o={26'd0,n};end
                    4:begin core_addr_o=6;core_data_o={29'd0,batch};end
                    5:begin core_addr_o=8;core_data_o=d[3];end
                    default:begin end
                endcase
            end
            START_FC:begin core_req_o=1;core_we_o=1;core_addr_o=0;core_data_o=1;end
            POST_READ:begin
                core_req_o=1;
                core_addr_o=op==1 ? 12'd1280+({10'd0,sample_q[1:0]}<<5)+element_q :
                    input_mmio[13:2]+(element_q>>2);
            end
            default:begin end
        endcase
    end
    wire scale_start=state==POST_VALUE && op==1 || state==ACT_PREP && activation<4;
    wire signed [7:0] activation_input=(activation==1 || activation==2) && quant_q<0 ? 8'sd0:quant_q;
    wire negative_branch=activation==3 && quant_q<0;
    wire signed [21:0] scale_input=state==POST_VALUE ? core_data_i[21:0]:{{14{activation_input[7]}},activation_input};
    wire signed [31:0] scale_multiplier=state==POST_VALUE ? d[7]:negative_branch ? d[10]:d[9];
    wire [4:0] scale_shift=state==POST_VALUE ? d[8][4:0]:negative_branch ? d[8][20:16]:d[8][12:8];
    wire scale_done,scale_busy;
    wire signed [7:0] scale_value;
    har_task_scale scaler(.clk_i(clk_i),.rst_ni(rst_ni),.start_i(scale_start),
        .value_i(scale_input),.multiplier_i(scale_multiplier),.shift_i(scale_shift),
        .busy_o(scale_busy),.done_o(scale_done),.value_o(scale_value));
    logic [31:0] reg_read;
    always_comb begin
        reg_read=0;
        case(reg_addr_i)
            4:reg_read={27'd0,rejected_q,valid_q,failed_q,busy_o,done_q};
            8:reg_read=base_cfg;
            12:reg_read=count_cfg;
            16:reg_read=32'h014020bf; // all six acts, forwarding; no LUT cache
            20:reg_read={24'd0,index_q};
            24:reg_read={28'd0,error_q};
            28:reg_read=cycles_q;
            32:reg_read={24'd0,completed_q};
            36:reg_read={28'd0,reject_q};
            default:begin end
        endcase
    end
    wire transfer_finished=!dma_busy_i && dma_done_i;
    integer j;
    always_ff @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            state<=IDLE;base_cfg<=0;count_cfg<=0;base_q<=0;count_q<=0;index_q<=0;completed_q<=0;
            cycles_q<=0;done_q<=0;failed_q<=0;valid_q<=0;rejected_q<=0;error_q<=0;reject_q<=0;
            received_q<=0;ingress_count_q<=0;ingress_bad_q<=0;bias_bad_q<=0;sample_q<=0;element_q<=0;word_q<=0;config_q<=0;
            partial_q<=0;forward_q<=0;partial_context_q<=0;partial_n_q<=0;forward_n_q<=0;
            partial_batch_q<=0;forward_batch_q<=0;quant_q<=0;output_q<=0;lut_word_q<=0;reg_data_o<=0;
            for(j=0;j<16;j=j+1)d[j]<=0;
        end else begin
            reg_data_o<=reg_req_i && !reg_we_i ? reg_read:32'd0;
            if(busy_o)cycles_q<=cycles_q+1'b1;
            if(legacy_start_i)begin valid_q<=0;partial_q<=0;forward_q<=0;end
            if(reject_i || (busy_o && cpu_write) || (start && (core_busy_i || dma_busy_i))) begin
                rejected_q<=1;reject_q<=E_BUSY;
            end else if(cpu_write && !busy_o) begin
                if(ack) begin done_q<=0;failed_q<=0;valid_q<=0;rejected_q<=0;error_q<=0;reject_q<=0;end
                else if(reg_addr_i==8)base_cfg<=reg_data_i;
                else if(reg_addr_i==12)count_cfg<=reg_data_i;
                else if(!start)begin rejected_q<=1;reject_q<=E_VALUE;end
            end
            if(dma_start_o)begin received_q<=0;ingress_count_q<=0;ingress_bad_q<=0;bias_bad_q<=0;end
            if(ingress_i && busy_o)begin
                if(desc_ingress || input_ingress || bias_ingress || lut_ingress)begin
                    ingress_count_q<=ingress_count_q+1'b1;
                    if(ingress_addr_i!=(desc_ingress ? 32'h70001640 : input_ingress ? input_mmio :
                        bias_ingress ? 32'h700009c0:32'h70001700)+({26'd0,ingress_count_q}<<2))ingress_bad_q<=1;
                end
                if(desc_ingress)begin d[ingress_addr_i[5:2]]<=ingress_data_i;received_q[ingress_addr_i[5:2]]<=1;end
                else if(input_ingress)received_q[(ingress_addr_i-input_mmio)>>2]<=1;
                else if(bias_ingress)begin
                    if(ingress_data_i[31:22]!={10{ingress_data_i[21]}})bias_bad_q<=1;
                end else if(lut_ingress)begin lut_word_q<=ingress_data_i;received_q[0]<=1;end
                else if(!tile_ingress)ingress_bad_q<=1;
            end
            case(state)
                IDLE:if(start && !core_busy_i && !dma_busy_i)begin
                    done_q<=0;failed_q<=0;valid_q<=0;rejected_q<=0;error_q<=0;reject_q<=0;
                    index_q<=0;completed_q<=0;cycles_q<=0;partial_q<=0;forward_q<=0;
                    base_q<=base_cfg;count_q<=count_cfg[7:0];
                    if(base_cfg[5:0]!=0)begin done_q<=1;failed_q<=1;error_q<=E_ALIGN;end
                    else if(count_cfg<1 || count_cfg>128)begin done_q<=1;failed_q<=1;error_q<=E_VALUE;end
                    else if(!region(base_cfg,count_cfg<<6))begin done_q<=1;failed_q<=1;error_q<=E_RANGE;end
                    else state<=FETCH;
                end
                FETCH:state<=WAIT_DESC;
                WAIT_DESC:if(transfer_finished)begin
                    if(dma_error_i || ingress_bad_q || received_q!=16'hffff || ingress_count_q!=16)begin error_q<=E_DMA;state<=DRAIN;end
                    else state<=CHECK;
                end
                CHECK:begin
                    sample_q<=0;word_q<=0;element_q<=0;config_q<=0;
                    if(descriptor_error!=0)begin error_q<=descriptor_error;state<=DRAIN;end
                    else if(input_internal)state<=FWD_READ;
                    else state<=INPUT;
                end
                INPUT:state<=WAIT_INPUT;
                WAIT_INPUT:if(transfer_finished)begin
                    if(dma_error_i || ingress_bad_q || received_q!=(16'hffff>>(16-input_words)) || ingress_count_q!={1'b0,input_words})begin error_q<=E_DMA;state<=DRAIN;end
                    else if(sample_q+1<batch)begin sample_q<=sample_q+1'b1;state<=INPUT;end
                    else begin
                        sample_q<=0;
                        if(op==2)state<=POST_READ;
                        else if(initialize)state<=BIAS;
                        else state<=CONFIG;
                    end
                end
                BIAS:state<=WAIT_BIAS;
                WAIT_BIAS:if(transfer_finished)begin
                    if(dma_error_i || ingress_bad_q || bias_bad_q || ingress_count_q!=n)begin error_q<=bias_bad_q ? E_VALUE:E_DMA;state<=DRAIN;end
                    else state<=CONFIG;
                end
                FWD_READ:state<=FWD_WRITE;
                FWD_WRITE:begin
                    if(word_q+1<input_words)begin word_q<=word_q+1'b1;state<=FWD_READ;end
                    else if(sample_q+1<batch)begin sample_q<=sample_q+1'b1;word_q<=0;state<=FWD_READ;end
                    else begin
                        sample_q<=0;word_q<=0;forward_q<=0;
                        if(op==2)state<=POST_READ;
                        else if(initialize)state<=BIAS;
                        else state<=CONFIG;
                    end
                end
                CONFIG:if(config_q==5)state<=START_FC;else config_q<=config_q+1'b1;
                START_FC:state<=WAIT_FC;
                WAIT_FC:if(!core_busy_i && core_done_i && !dma_busy_i)begin
                    if(core_error_i || dma_error_i || ingress_bad_q)begin error_q<=E_DMA;state<=DRAIN;end
                    else if(last_k)state<=POST_READ;
                    else state<=COMMIT;
                end
                POST_READ:state<=POST_VALUE;
                POST_VALUE:begin
                    if(op==1)state<=FC_SCALE;
                    else begin quant_q<=core_data_i[element_q[1:0]*8+:8];state<=ACT_PREP;end
                end
                FC_SCALE:if(scale_done)begin quant_q<=scale_value;state<=ACT_PREP;end
                ACT_PREP:if(activation>=4)state<=LUT;else state<=ACT_SCALE;
                ACT_SCALE:if(scale_done)begin
                    output_q<=activation==2 && scale_value>$signed(d[12][7:0]) ? d[12][7:0]:scale_value;
                    state<=STORE;
                end
                LUT:state<=WAIT_LUT;
                WAIT_LUT:if(transfer_finished)begin
                    if(dma_error_i || ingress_bad_q || !received_q[0] || ingress_count_q!=1)begin error_q<=E_DMA;state<=DRAIN;end
                    else begin output_q<=lut_word_q[lut_index[1:0]*8+:8];state<=STORE;end
                end
                STORE:begin
                    if(element_q+1<n)begin element_q<=element_q+1'b1;state<=POST_READ;end
                    else if(sample_q+1<batch)begin sample_q<=sample_q+1'b1;element_q<=0;state<=POST_READ;end
                    else begin
                        sample_q<=0;element_q<=0;
                        state<=keep ? COMMIT:OUTPUT;
                    end
                end
                OUTPUT:state<=WAIT_OUTPUT;
                WAIT_OUTPUT:if(transfer_finished)begin
                    if(dma_error_i || ingress_bad_q)begin error_q<=E_DMA;state<=DRAIN;end
                    else if(sample_q+1<batch)begin sample_q<=sample_q+1'b1;state<=OUTPUT;end
                    else state<=COMMIT;
                end
                COMMIT:begin
                    completed_q<=completed_q+1'b1;
                    partial_q<=!last_k;
                    partial_context_q<=d[13];partial_n_q<=n;partial_batch_q<=batch;
                    if(last_k)begin forward_q<=keep;forward_n_q<=n;forward_batch_q<=batch;end
                    if(index_q==count_q-1)begin done_q<=1;valid_q<=1;state<=IDLE;end
                    else begin index_q<=index_q+1'b1;state<=FETCH;end
                end
                DRAIN:begin
                    valid_q<=0;partial_q<=0;forward_q<=0;
                    if(!dma_busy_i && !core_busy_i && !scale_busy)begin
                        done_q<=1;failed_q<=1;state<=IDLE;
                    end
                end
                default:begin error_q<=E_DESC;state<=DRAIN;end
            endcase
        end
    end
endmodule
