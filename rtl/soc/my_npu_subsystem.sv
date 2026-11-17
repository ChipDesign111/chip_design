`timescale 1ns/1ps
module my_npu_subsystem #(parameter bit LUT_WORD_CACHE=0) (
    input logic clk_i,rst_ni,req_i,we_i,
    input logic [31:0] addr_i,wdata_i,
    output wire [31:0] rdata_o,
    input logic dma_write_i,dma_busy_i,dma_done_i,dma_error_i,dma_read_i,dma_write_active_i,
    output wire auto_start_o,
    output wire [31:0] auto_source_o,auto_dest_o,auto_words_o,
    output wire auto_task_o,
    output wire [3:0] auto_last_be_o,
    input logic [31:0] dma_rdata_i,
    output wire dma_req_o,dma_we_o,
    output wire [4:0] dma_addr_o,
    output wire [31:0] dma_wdata_o,
    output wire dma_conflict_o,npu_busy_o
);
    wire dma_select=addr_i[13:5]==9'h068;
    wire task_select=addr_i[13:6]==8'h58;
    wire private_window=addr_i[13:6]==8'h59 || addr_i[13:7]==7'h2d || addr_i[13:2]==12'h5c0;
    wire packed_window=addr_i[13:7]==7'h2d;
    wire task_busy,task_valid,core_busy,core_done,core_error;
    wire [31:0] npu_rdata,task_rdata;
    wire core_auto_start,task_auto_start,task_ingress_core,task_core_req,task_core_we;
    wire [31:0] core_source,core_dest,core_words,task_source,task_dest,task_words,task_core_data;
    wire [3:0] task_last_be;
    wire [11:0] task_core_addr;
    wire task_abort,task_invalidate,post_write;
    wire [6:0] post_index;
    wire [7:0] post_data;
    logic [1:0] read_select_q;
    wire cpu_write=req_i && we_i && !dma_write_i;
    wire private_cpu_write=cpu_write && private_window;
    wire legacy_start=cpu_write && addr_i[13:2]==0 && wdata_i[0] && !task_busy && !core_busy && !dma_busy_i;
    wire task_reject=cpu_write && !task_select && task_busy;
    wire packed_read=req_i && !we_i && packed_window && (task_busy || task_valid);
    wire tile_access=req_i && dma_write_i && addr_i[13:7]==7'h02;
    wire legacy_access=req_i && !task_select && !private_window && !dma_select && !task_busy;
    wire core_enable=task_core_req || task_ingress_core || packed_read ||
        (task_busy ? tile_access:legacy_access);
    wire core_write=task_core_req ? task_core_we:we_i;
    wire [11:0] core_address=task_core_req ? task_core_addr:addr_i[13:2];
    wire [31:0] core_wdata=task_core_req ? task_core_data:wdata_i;
    // axi2mem exposes WUSER even during reads/idle. It is a write owner only
    // for a real external write, never for the internal configuration port.
    wire core_dma_write=req_i && we_i && dma_write_i && !task_ingress_core && !task_core_req;
    wire core_task_access=task_core_req || task_ingress_core || packed_read;
    always_ff @(posedge clk_i or negedge rst_ni)
        if(!rst_ni)read_select_q<=0;
        else if(req_i && !we_i)begin
            if(task_select)read_select_q<=2;
            else if(dma_select)read_select_q<=1;
            else if(task_busy && !packed_read)read_select_q<=3;
            else read_select_q<=0;
        end else read_select_q<=0;
    assign rdata_o=read_select_q==2 ? task_rdata:read_select_q==1 ? dma_rdata_i:
        read_select_q==3 ? 32'd0:npu_rdata;
    assign dma_req_o=req_i && dma_select && !(task_busy && we_i);
    assign dma_we_o=we_i;
    assign dma_addr_o=addr_i[4:0];
    assign dma_wdata_o=wdata_i;
    assign dma_conflict_o=1'b0;
    assign npu_busy_o=core_busy || task_busy;
    assign auto_start_o=task_auto_start || (core_auto_start && !task_abort);
    assign auto_task_o=task_auto_start;
    assign auto_source_o=task_auto_start ? task_source:core_source;
    assign auto_dest_o=task_auto_start ? task_dest:core_dest;
    assign auto_words_o=task_auto_start ? task_words:core_words;
    assign auto_last_be_o=task_auto_start ? task_last_be:4'hf;
    har_task_engine #(.LUT_WORD_CACHE(LUT_WORD_CACHE)) tasks (
        .clk_i(clk_i),.rst_ni(rst_ni),
        .reg_req_i((req_i && task_select && (!we_i || !dma_write_i)) || (private_cpu_write && !task_busy)),
        .reg_we_i(we_i),.reg_addr_i(private_cpu_write ? 6'h3c:addr_i[5:0]),.reg_data_i(wdata_i),.reg_data_o(task_rdata),
        .reject_i(task_reject),.legacy_start_i(legacy_start),
        .core_busy_i(core_busy),.core_done_i(core_done),.core_error_i(core_error),.core_data_i(npu_rdata),
        .core_req_o(task_core_req),.core_we_o(task_core_we),.core_addr_o(task_core_addr),.core_data_o(task_core_data),
        .core_abort_o(task_abort),.core_invalidate_o(task_invalidate),
        .post_write_o(post_write),.post_index_o(post_index),.post_data_o(post_data),
        .dma_busy_i(dma_busy_i),.dma_done_i(dma_done_i),.dma_error_i(dma_error_i),
        .ingress_i(req_i && we_i && dma_write_i),.ingress_addr_i(addr_i),.ingress_data_i(wdata_i),
        .ingress_core_o(task_ingress_core),.dma_start_o(task_auto_start),
        .dma_source_o(task_source),.dma_dest_o(task_dest),.dma_words_o(task_words),.dma_last_be_o(task_last_be),
        .busy_o(task_busy),.output_valid_o(task_valid));
    simple_npu_top i_npu_core (
        .clka(clk_i),.rst_ni(rst_ni),.ena(core_enable),.wea(core_write),.addra(core_address),.dina(core_wdata),.douta(npu_rdata),
        .task_access_i(core_task_access),.task_abort_i(task_abort),.task_invalidate_i(task_invalidate),
        .task_write_i(post_write),.task_index_i(post_index),.task_data_i(post_data),
        .task_done_o(core_done),.task_error_o(core_error),
        .dma_write_i(core_dma_write),.dma_busy_i(dma_busy_i),.dma_done_i(dma_done_i),.dma_error_i(dma_error_i),
        .dma_read_i(dma_read_i),.dma_write_active_i(dma_write_active_i),
        .auto_start_o(core_auto_start),.auto_source_o(core_source),.auto_dest_o(core_dest),.auto_words_o(core_words),
        .busy_o(core_busy));
endmodule
