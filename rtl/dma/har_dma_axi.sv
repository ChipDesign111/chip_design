// AXI metadata adapter. USER=1 marks DMA writes at the NPU ingress.
module har_dma_axi (
    input logic clk_i, rst_ni,
    input logic reg_req_i, reg_we_i,
    input logic [4:0] reg_addr_i,
    input logic [31:0] reg_wdata_i,
    output wire [31:0] reg_rdata_o,
    input logic npu_busy_i, conflict_i,
    input logic stream_ready_i,
    output wire busy_o,
    output wire stream_commit_o,stream_abort_o,
    output wire [1:0] stream_commit_count_o,
    AXI_BUS.Master master
);
    assign master.ar_id='0;
    assign master.ar_size=3'd2;
    assign master.ar_burst=2'b01;
    assign master.ar_lock=0;assign master.ar_cache=0;assign master.ar_prot=0;
    assign master.ar_qos=0;assign master.ar_region=0;assign master.ar_user=1;
    assign master.aw_id='0;
    assign master.aw_size=3'd2;
    assign master.aw_burst=2'b01;
    assign master.aw_lock=0;assign master.aw_cache=0;assign master.aw_prot=0;
    assign master.aw_qos=0;assign master.aw_region=0;assign master.aw_atop=0;
    assign master.aw_user=1;assign master.w_user=1;assign master.w_strb=4'hf;
    har_stream_dma i_engine (
        .stream_ready_i(stream_ready_i),
        .stream_commit_o(stream_commit_o),.stream_abort_o(stream_abort_o),.stream_commit_count_o(stream_commit_count_o),
        .clk_i(clk_i),.rst_ni(rst_ni),.reg_req_i(reg_req_i),.reg_we_i(reg_we_i),
        .reg_addr_i(reg_addr_i),.reg_wdata_i(reg_wdata_i),.reg_rdata_o(reg_rdata_o),
        .npu_busy_i(npu_busy_i),.conflict_i(conflict_i),.busy_o(busy_o),
        .ar_addr_o(master.ar_addr),.ar_len_o(master.ar_len),.ar_valid_o(master.ar_valid),.ar_ready_i(master.ar_ready),
        .r_data_i(master.r_data),.r_resp_i(master.r_resp),.r_last_i(master.r_last),.r_valid_i(master.r_valid),.r_ready_o(master.r_ready),
        .aw_addr_o(master.aw_addr),.aw_len_o(master.aw_len),.aw_valid_o(master.aw_valid),.aw_ready_i(master.aw_ready),
        .w_data_o(master.w_data),.w_last_o(master.w_last),.w_valid_o(master.w_valid),.w_ready_i(master.w_ready),
        .b_resp_i(master.b_resp),.b_valid_i(master.b_valid),.b_ready_o(master.b_ready)
    );
endmodule
