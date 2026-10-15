// Bounded SRAM-to-NPU AXI4 burst copier, one outstanding burst, 16-word buffer.
// MMIO offsets are relative to NPU+0xD00. No vendor IP is used.
module har_dma (
    input logic clk_i, rst_ni,
    input logic reg_req_i, reg_we_i,
    input logic [4:0] reg_addr_i,
    input logic [31:0] reg_wdata_i,
    output logic [31:0] reg_rdata_o,
    input logic npu_busy_i, conflict_i,
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
    localparam [2:0] IDLE=0, PREP=1, AR=2, READ=3, WRITE=4, RESP=5;
    logic [2:0] state;
    logic [31:0] source_cfg, dest_cfg, count_cfg;
    logic [31:0] source_q, dest_q, remaining, cycles, copied, error_code;
    logic [4:0] burst_words, read_count, write_count;
    logic done, error, aw_done, w_done, read_error;
    logic [31:0] buffer [0:15];
    logic [31:0] reg_data;
    logic [10:0] src_boundary, dst_boundary;
    logic [31:0] next_words;
    wire start = reg_req_i && reg_we_i && reg_addr_i==0 && reg_wdata_i[0];
    wire ack = reg_req_i && reg_we_i && reg_addr_i==0 && reg_wdata_i[1];
    wire [32:0] source_end = {1'b0,source_cfg}+({1'b0,count_cfg}<<2);
    wire [32:0] dest_end = {1'b0,dest_cfg}+({1'b0,count_cfg}<<2);
    wire valid_source = count_cfg>0 && count_cfg<=2048 && source_cfg[1:0]==0 &&
        source_cfg>=32'h80000000 && source_end<=33'h080002000;
    wire valid_dest = dest_cfg[1:0]==0 && (
        (dest_cfg>=32'h70000100 && dest_end<=33'h070000a58) ||
        (dest_cfg>=32'h70000040 && dest_end<=33'h070000080) ||
        (dest_cfg>=32'h70000c00 && dest_end<=33'h070000c40));
    assign busy_o = state!=IDLE;
    assign ar_addr_o=source_q;
    assign aw_addr_o=dest_q;
    assign ar_len_o=burst_words-1'b1;
    assign aw_len_o=burst_words-1'b1;
    assign ar_valid_o=state==AR;
    assign r_ready_o=state==READ;
    assign aw_valid_o=state==WRITE && !aw_done;
    assign w_valid_o=state==WRITE && !w_done;
    assign w_data_o=buffer[write_count[3:0]];
    assign w_last_o=write_count+1'b1==burst_words;
    assign b_ready_o=state==RESP;
    // Keep the FIFO data array off the reset tree for RAM inference.
    always_ff @(posedge clk_i)
        if(rst_ni && state==READ && r_valid_i && read_count<burst_words)
            buffer[read_count[3:0]]<=r_data_i;
    always_comb begin
        src_boundary=11'd1024-{1'b0,source_q[11:2]};
        dst_boundary=11'd1024-{1'b0,dest_q[11:2]};
        next_words=remaining>16 ? 32'd16:remaining;
        if(next_words>src_boundary) next_words=src_boundary;
        if(next_words>dst_boundary) next_words=dst_boundary;
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
            state<=IDLE;source_cfg<=0;dest_cfg<=0;count_cfg<=0;
            source_q<=0;dest_q<=0;remaining<=0;cycles<=0;copied<=0;
            burst_words<=0;read_count<=0;write_count<=0;
            done<=0;error<=0;error_code<=0;aw_done<=0;w_done<=0;read_error<=0;
            reg_rdata_o<=0;
        end else begin
            reg_rdata_o<=reg_req_i && !reg_we_i ? reg_data:32'd0;
            if(busy_o) cycles<=cycles+1'b1;
            if(conflict_i || (busy_o && reg_req_i && reg_we_i)) begin
                error<=1;error_code<=7;
            end
            if(!busy_o && reg_req_i && reg_we_i) begin
                case(reg_addr_i)
                    8:source_cfg<=reg_wdata_i;
                    12:dest_cfg<=reg_wdata_i;
                    16:count_cfg<=reg_wdata_i;
                    default:begin end
                endcase
            end
            case(state)
                IDLE:begin
                    if(start) begin
                        cycles<=0;copied<=0;error<=0;error_code<=0;done<=0;
                        if(!valid_source || !valid_dest) begin
                            error<=1;error_code<=1;done<=1;
                        end else if(npu_busy_i) begin
                            error<=1;error_code<=2;done<=1;
                        end else begin
                            source_q<=source_cfg;dest_q<=dest_cfg;remaining<=count_cfg;state<=PREP;
                        end
                    end else if(ack) begin done<=0;error<=0;error_code<=0;end
                end
                PREP:begin burst_words<=next_words[4:0];read_count<=0;read_error<=0;state<=AR;end
                AR:if(ar_ready_i) state<=READ;
                READ:if(r_valid_i) begin
                    if(r_resp_i!=0 || r_last_i!=(read_count+1'b1==burst_words)) begin
                        read_error<=1;error<=1;error_code<=r_resp_i!=0 ? 4:5;
                    end
                    if(read_count<31) read_count<=read_count+1'b1;
                    if(r_last_i) begin
                        if(read_error || r_resp_i!=0 || read_count+1'b1!=burst_words) begin
                            state<=IDLE;done<=1;
                        end else begin state<=WRITE;aw_done<=0;w_done<=0;write_count<=0;end
                    end
                end
                WRITE:begin
                    if(aw_valid_o && aw_ready_i) aw_done<=1;
                    if(w_valid_o && w_ready_i) begin
                        if(w_last_o) w_done<=1;
                        else write_count<=write_count+1'b1;
                    end
                    if((aw_done || aw_ready_i) && (w_done || (w_ready_i && w_last_o))) state<=RESP;
                end
                RESP:if(b_valid_i) begin
                    if(b_resp_i!=0) begin error<=1;error_code<=6;done<=1;state<=IDLE;end
                    else begin
                        copied<=copied+burst_words;
                        if(remaining==burst_words) begin done<=1;state<=IDLE;end
                        else begin
                            source_q<=source_q+({27'd0,burst_words}<<2);
                            dest_q<=dest_q+({27'd0,burst_words}<<2);
                            remaining<=remaining-burst_words;state<=PREP;
                        end
                    end
                end
                default:state<=IDLE;
            endcase
        end
    end
endmodule
