// Streaming SRAM-to-tile AXI4 DMA: independent read/write channels, two-word FIFO.
module har_dma (
    input logic clk_i, rst_ni,
    input logic reg_req_i, reg_we_i,
    input logic [4:0] reg_addr_i,
    input logic [31:0] reg_wdata_i,
    output logic [31:0] reg_rdata_o,
    input logic npu_busy_i, conflict_i,
    input logic auto_start_i,
    input logic [31:0] auto_source_i,auto_dest_i,auto_words_i,
    output wire done_o,error_o,read_active_o,write_active_o,
    output wire busy_o,
    output wire [31:0] ar_addr_o, aw_addr_o,
    output wire [7:0] ar_len_o, aw_len_o,
    output wire ar_valid_o, aw_valid_o,
    input logic ar_ready_i, aw_ready_i,
    input logic [31:0] r_data_i,
    input logic [1:0] r_resp_i,
    input logic r_last_i, r_valid_i,
    output wire r_ready_o,
    output wire [31:0] w_data_o,
    output wire w_last_o, w_valid_o,
    input logic w_ready_i,
    input logic [1:0] b_resp_i,
    input logic b_valid_i,
    output wire b_ready_o
);
    localparam [1:0] IDLE=0,PREP=1,COPY=2,RESP=3;
    logic [1:0] state;
    logic [31:0] source_cfg,dest_cfg,count_cfg,source_q,dest_q,remaining,cycles,copied,error_code;
    logic [4:0] burst_words,read_count,write_count;
    logic ar_done,aw_done,read_done,write_done,done,error,read_error;
    logic [31:0] fifo[0:1];
    logic read_ptr,write_ptr;
    logic [1:0] occupancy;
    wire start=reg_req_i && reg_we_i && reg_addr_i==0 && reg_wdata_i[0];
    wire ack=reg_req_i && reg_we_i && reg_addr_i==0 && reg_wdata_i[1];
    wire [31:0] cfg_source=auto_start_i ? auto_source_i:source_cfg;
    wire [31:0] cfg_dest=auto_start_i ? auto_dest_i:dest_cfg;
    wire [31:0] cfg_count=auto_start_i ? auto_words_i:count_cfg;
    wire [32:0] source_end={1'b0,cfg_source}+({1'b0,cfg_count}<<2);
    wire [32:0] dest_end={1'b0,cfg_dest}+({1'b0,cfg_count}<<2);
    wire valid_source=cfg_count>0 && cfg_count<=2048 && cfg_source[1:0]==0 &&
        cfg_source>=32'h80000000 && source_end<=33'h080002000;
    wire valid_dest=cfg_dest[1:0]==0 && cfg_dest>=32'h70000100 && dest_end<=33'h070000180;
    function automatic [4:0] burst_size(input logic [31:0] src,dst,count);
        logic [31:0] n,src_boundary,dst_boundary;
        begin
            src_boundary=1024-{22'd0,src[11:2]};dst_boundary=1024-{22'd0,dst[11:2]};
            n=count>16 ? 16:count;
            if(n>src_boundary) n=src_boundary;
            if(n>dst_boundary) n=dst_boundary;
            burst_size=n[4:0];
        end
    endfunction
    assign busy_o=state!=IDLE;
    assign done_o=done;assign error_o=error;
    assign ar_addr_o=source_q;assign aw_addr_o=dest_q;
    assign ar_len_o=burst_words-1'b1;assign aw_len_o=burst_words-1'b1;
    assign ar_valid_o=state==COPY && !ar_done;
    assign aw_valid_o=state==COPY && !aw_done;
    assign w_valid_o=state==COPY && aw_done && occupancy!=0 && !write_done;
    assign w_data_o=fifo[read_ptr];
    assign w_last_o=write_count+1'b1==burst_words;
    wire pop=w_valid_o && w_ready_i;
    assign r_ready_o=state==COPY && ar_done && !read_done &&
        (read_count>=burst_words || occupancy<2 || pop);
    wire receive=r_ready_o && r_valid_i;
    // On malformed early RLAST, complete the already-issued write burst with
    // zero padding, then report failure. The NPU never publishes that bank.
    wire pad=state==COPY && read_done && read_count<burst_words && (occupancy<2 || pop);
    wire push=(receive && read_count<burst_words) || pad;
    assign b_ready_o=state==RESP;
    assign read_active_o=receive;
    assign write_active_o=pop;
    always_ff @(posedge clk_i) if(push) fifo[write_ptr]<=pad ? 32'd0:r_data_i;
    logic [31:0] reg_data;
    always_comb begin
        reg_data=0;
        case(reg_addr_i)
            4:reg_data={29'b0,error,busy_o,done};
            8:reg_data=source_cfg;
            12:reg_data=dest_cfg;
            16:reg_data=count_cfg;
            20:reg_data=cycles;
            24:reg_data=copied;
            28:reg_data=error_code;
            default:reg_data=0;
        endcase
    end
    always_ff @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            state<=IDLE;source_cfg<=0;dest_cfg<=0;count_cfg<=0;source_q<=0;dest_q<=0;
            remaining<=0;cycles<=0;copied<=0;error_code<=0;burst_words<=0;read_count<=0;write_count<=0;
            ar_done<=0;aw_done<=0;read_done<=0;write_done<=0;done<=0;error<=0;read_error<=0;
            read_ptr<=0;write_ptr<=0;occupancy<=0;reg_rdata_o<=0;
        end else begin
            reg_rdata_o<=reg_req_i && !reg_we_i ? reg_data:32'd0;
            if(busy_o) cycles<=cycles+1'b1;
            if(conflict_i || (busy_o && reg_req_i && reg_we_i)) begin error<=1;error_code<=7;end
            if(!busy_o && reg_req_i && reg_we_i) case(reg_addr_i)
                8:source_cfg<=reg_wdata_i;
                12:dest_cfg<=reg_wdata_i;
                16:count_cfg<=reg_wdata_i;
                default:begin end
            endcase
            case(state)
                IDLE:begin
                    if(auto_start_i || start) begin
                        cycles<=0;copied<=0;done<=0;error<=0;error_code<=0;
                        if(!valid_source || !valid_dest || (npu_busy_i && !auto_start_i)) begin
                            error<=1;error_code<=1;done<=1;
                        end else begin
                            source_q<=cfg_source;dest_q<=cfg_dest;remaining<=cfg_count;
                            burst_words<=burst_size(cfg_source,cfg_dest,cfg_count);
                            ar_done<=0;aw_done<=0;read_done<=0;write_done<=0;read_error<=0;
                            occupancy<=0;read_ptr<=0;write_ptr<=0;read_count<=0;write_count<=0;state<=COPY;
                        end
                    end else if(ack) begin done<=0;error<=0;error_code<=0;end
                end
                PREP:begin
                    burst_words<=burst_size(source_q,dest_q,remaining);
                    ar_done<=0;aw_done<=0;read_done<=0;write_done<=0;read_error<=0;
                    occupancy<=0;read_ptr<=0;write_ptr<=0;read_count<=0;write_count<=0;state<=COPY;
                end
                COPY:begin
                    if(ar_valid_o && ar_ready_i) ar_done<=1;
                    if(aw_valid_o && aw_ready_i) aw_done<=1;
                    case({push,pop})
                        2'b10:occupancy<=occupancy+1'b1;
                        2'b01:occupancy<=occupancy-1'b1;
                        default:begin end
                    endcase
                    if(push) write_ptr<=~write_ptr;
                    if(pop) begin
                        read_ptr<=~read_ptr;write_count<=write_count+1'b1;
                        if(w_last_o) write_done<=1;
                    end
                    if(receive) begin
                        if(read_count<31) read_count<=read_count+1'b1;
                        if(r_resp_i!=0 || r_last_i!=(read_count+1'b1==burst_words)) begin
                            read_error<=1;error<=1;error_code<=r_resp_i!=0 ? 4:5;
                        end
                        if(r_last_i) read_done<=1;
                    end
                    if(pad) read_count<=read_count+1'b1;
                    if(read_done && write_done && aw_done) state<=RESP;
                end
                RESP:if(b_valid_i) begin
                    if(b_resp_i!=0 || read_error) begin
                        error<=1;if(b_resp_i!=0) error_code<=6;done<=1;state<=IDLE;
                    end else begin
                        copied<=copied+{27'd0,burst_words};
                        if(remaining=={27'd0,burst_words}) begin done<=1;state<=IDLE;end
                        else begin
                            source_q<=source_q+({27'd0,burst_words}<<2);dest_q<=dest_q+({27'd0,burst_words}<<2);
                            remaining<=remaining-{27'd0,burst_words};state<=PREP;
                        end
                    end
                end
                default:state<=IDLE;
            endcase
        end
    end
endmodule
