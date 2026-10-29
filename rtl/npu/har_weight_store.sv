// Two 64-byte tile buffers shared by both layers. FC1 exposes one 64-byte
// weight tile per bank. FC2 exposes eight six-byte rows packed into 48 bytes.
// The loader exclusively owns an unpublished bank. Data requires no reset.
module har_weight_store (
    input logic clk,we_i,bank_i,
    input logic [3:0] word_i,
    input logic [31:0] data_i,
    input logic compute_bank_i,
    output wire [511:0] tile_o
);
    (* ram_style = "registers" *) logic [511:0] tiles[0:1];
    always_ff @(posedge clk) if(we_i) tiles[bank_i][word_i*32+:32]<=data_i;
    assign tile_o=tiles[compute_bank_i];
endmodule
