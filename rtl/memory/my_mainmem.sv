// One-cycle AXI memory timing with a phase-separated physical SRAM port.
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
    // Accept the transaction on the same rising edge as axi2mem. Execute it
    // at the following falling edge, leaving the read data available before
    // the next rising-edge AXI response handshake. No extra AXI cycle is added.
    //
    // Reset does not asynchronously clear these pins. An already accepted
    // access completes with stable address/data/mask; later rising edges stop
    // accepting requests while reset is low. Payload registers deliberately
    // have no reset, so reset cannot tear an in-flight SRAM transaction.
    logic port_req_q;
    logic [ADDR_W-1:0] port_addr_q;
    logic [DATA_W-1:0] port_wdata_q;
    logic [3:0] port_byte_we_q;
    wire sram_clk = ~clk_i;

    always_ff @(posedge clk_i) begin
        port_req_q <= rst_ni && req_i;
        if (rst_ni && req_i) begin
            port_addr_q <= addr_i[12:2];
            port_wdata_q <= wdata_i;
            port_byte_we_q <= be_i & {4{we_i}};
        end
    end

    // SRAM contents are not reset. FPGA INIT_FILE remains supported.
`ifndef SYNTHESIS
    initial begin
        if (ADDR_W != 11 || DATA_W != 32)
            $fatal(1, "SRAM adapter requires 2048 x 32");
    end
`endif
    chip_sram_2048x32 #(
        .INIT_FILE(INIT_FILE)
    ) i_sram (
        .clk_i(sram_clk), .req_i(port_req_q),
        .byte_we_i(port_byte_we_q), .addr_i(port_addr_q),
        .wdata_i(port_wdata_q), .rdata_o(rdata_o)
    );
endmodule
