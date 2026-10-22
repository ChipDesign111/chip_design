// Safe immutable trampoline plus explicit firmware commit register.
// ASIC: load all 2048 words sequentially through SRAM port, then commit.
// FPGA: a non-empty INIT_FILE statically selects the initialized BRAM path.
module bootram #(
    parameter bit PREINITIALIZED=0
)(
    input logic clk_i,rst_ni,req_i,wen_i,
    input logic [3:0] addr_i,
    input logic [31:0] data_i,
    input logic sram_write_i,
    input logic [31:0] sram_addr_i,
    input logic [3:0] sram_be_i,
    output logic ready_o,
    output logic [31:0] data_o
);
    logic [11:0] loaded_words;
    logic [3:0] release_margin;
    wire commit=req_i && wen_i && addr_i==15 && data_i==32'hb007c0de;
    wire reload=req_i && wen_i && addr_i==15 && data_i==0;
    always_ff @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            loaded_words<=PREINITIALIZED ? 12'd2048:12'd0;
            release_margin<=0;ready_o<=0;data_o<=0;
        end else begin
            // In-order, full-word coverage is required. Merely writing the
            // last word, partially writing a word, or issuing the key is insufficient.
            if(!ready_o && loaded_words<2048 && sram_write_i && sram_be_i==4'hf &&
               sram_addr_i==32'h80000000+({20'd0,loaded_words}<<2))
                loaded_words<=loaded_words+1'b1;
            if((commit && loaded_words==2048) || PREINITIALIZED)
                release_margin<={release_margin[2:0],1'b1};
            else if(release_margin!=0) release_margin<={release_margin[2:0],1'b1};
            if(release_margin[3]) ready_o<=1;
            if(reload) begin loaded_words<=0;release_margin<=0;ready_o<=0;end
            if(req_i && !wen_i) case(addr_i)
                0:data_o<=32'h800002b7; // lui t0,0x80000
                1:data_o<=32'h00028067; // jalr zero,0(t0)
                15:data_o<={18'd0,ready_o,1'b0,loaded_words};
                default:data_o<=32'h0000006f; // jal zero,0: safe trap loop
            endcase
        end
    end
endmodule
