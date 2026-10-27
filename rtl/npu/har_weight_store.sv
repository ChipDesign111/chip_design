// Two 64-byte tile buffers. FC2 packs eight six-byte tiles into each bank;
// the compute-side tile view keeps the original six INT8 weight bytes.
// The loader exclusively owns an unpublished bank. Data requires no reset.
module har_weight_store (
    input logic clk,we_i,bank_i,
    input logic [3:0] word_i,
    input logic [31:0] data_i,
    input logic compute_bank_i,
    input logic packed_i,
    input logic [4:0] tile_index_i,
    output wire [511:0] tile_o
);
    logic [511:0] tiles[0:1];
    always_ff @(posedge clk) if(we_i) tiles[bank_i][word_i*32+:32]<=data_i;
    genvar j;
    generate for(j=0;j<6;j=j+1) begin: tile_bytes
        assign tile_o[j*8+:8]=packed_i ?
            tiles[compute_bank_i][tile_index_i[2:0]*48+j*8+:8]:
            tiles[compute_bank_i][j*8+:8];
    end endgenerate
    generate for(j=6;j<64;j=j+1) begin: unused_bytes
        assign tile_o[j*8+:8]=packed_i ? 8'd0:tiles[compute_bank_i][j*8+:8];
    end
    endgenerate
endmodule
