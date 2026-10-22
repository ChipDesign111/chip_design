`timescale 1ns/1ps

module my_npu_subsystem (
    input  logic        clk_i,
    input  logic        rst_ni,
    input  logic        req_i,
    input  logic        we_i,
    input  logic [31:0] addr_i,
    input  logic [31:0] wdata_i,
    output wire [31:0] rdata_o,
    input logic dma_write_i, dma_busy_i,dma_done_i,dma_error_i,dma_read_i,dma_write_active_i,
    output wire auto_start_o,
    output wire [31:0] auto_source_o,auto_dest_o,auto_words_o,
    input logic [31:0] dma_rdata_i,
    output wire dma_req_o, dma_we_o,
    output wire [4:0] dma_addr_o,
    output wire [31:0] dma_wdata_o,
    output wire dma_conflict_o, npu_busy_o
);
  wire dma_select=addr_i[13:5]==9'h068;
  wire block_write=1'b0; // Core owns configuration protection; DMA may fill only its reserved bank.
  wire [31:0] npu_rdata;
  logic dma_select_q;
  always_ff @(posedge clk_i or negedge rst_ni)
    if(!rst_ni) dma_select_q<=0;
    else dma_select_q<=req_i && !we_i && dma_select;
  assign rdata_o=dma_select_q ? dma_rdata_i:npu_rdata;
  assign dma_req_o=req_i && dma_select;
  assign dma_we_o=we_i;
  assign dma_addr_o=addr_i[4:0];
  assign dma_wdata_o=wdata_i;
  assign dma_conflict_o=req_i && block_write;

  simple_npu_top i_npu_core (
      .clka  (clk_i),
      .dma_write_i(dma_write_i),.dma_busy_i(dma_busy_i),.dma_done_i(dma_done_i),.dma_error_i(dma_error_i),
      .dma_read_i(dma_read_i),.dma_write_active_i(dma_write_active_i),
      .auto_start_o(auto_start_o),.auto_source_o(auto_source_o),.auto_dest_o(auto_dest_o),.auto_words_o(auto_words_o),
      .wea   (we_i),
      .ena   (req_i && !dma_select && !block_write),
      .addra (addr_i[13:2]),
      .dina  (wdata_i),
      .douta (npu_rdata),
      .busy_o(npu_busy_o),
      .rst_ni(rst_ni)
  );

endmodule
