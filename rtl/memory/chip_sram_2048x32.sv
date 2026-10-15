// Project-owned single-port memory interface. No vendor implementation included.
module chip_sram_2048x32 (
    input  logic        clk_i,
    input  logic        req_i,
    input  logic [3:0]  byte_we_i,
    input  logic [10:0] addr_i,
    input  logic [31:0] wdata_i,
    output wire  [31:0] rdata_o
);
`ifdef CHIP_USE_RA1SHD
    // Active-low enable and per-byte write enables; output always enabled.
    RA1SHD_2048x32M8 i_macro (
        .CLK(clk_i), .CEN(~req_i), .WEN(~byte_we_i),
        .A(addr_i), .D(wdata_i), .Q(rdata_o), .OEN(1'b0)
    );
`else
    // Portable functional backend, uninitialized and without a data reset.
    // Read-during-write output is not part of the interface contract.
    logic [31:0] memory [0:2047];
    logic [31:0] read_q;
    assign rdata_o = read_q;
    always @(posedge clk_i) begin
        if (req_i) begin
            if (byte_we_i == 4'b0) read_q <= memory[addr_i];
            for (int byte_index = 0; byte_index < 4; byte_index = byte_index + 1)
                if (byte_we_i[byte_index])
                    memory[addr_i][byte_index*8 +: 8] <= wdata_i[byte_index*8 +: 8];
        end
    end
`endif
endmodule
