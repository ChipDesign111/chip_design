// Alternative compile-time implementation of the frozen my_mainmem interface.
module my_mainmem #(
    parameter int ADDR_W = 11,
    parameter int DATA_W = 32,
    parameter INIT_FILE = ""
) (
    input  logic              clk_i,
    input  logic              rst_ni,
    input  logic              req_i,
    input  logic              we_i,
    input  logic [3:0]        be_i,
    input  logic [31:0]       addr_i,
    input  logic [DATA_W-1:0] wdata_i,
    output wire [DATA_W-1:0] rdata_o
);
    // SRAM has no reset or hardware hex initialization. Like the reference
    // main memory, reset does not erase data. Simulation loads via port writes.
`ifndef SYNTHESIS
    initial begin
        if (ADDR_W != 11 || DATA_W != 32)
            $fatal(1, "SRAM adapter requires 2048 x 32");
        if (INIT_FILE != "")
            $fatal(1, "Use the SRAM testbench port loader, not INIT_FILE");
    end
`endif
    chip_sram_2048x32 i_sram (
        .clk_i(clk_i), .req_i(req_i),
        .byte_we_i(be_i & {4{we_i}}), .addr_i(addr_i[12:2]),
        .wdata_i(wdata_i), .rdata_o(rdata_o)
    );
endmodule
