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
    input logic [31:0] sram_wdata_i,
    output logic ready_o,
    output logic [31:0] data_o
);
    logic [11:0] loaded_words;
    logic [3:0] release_margin;
    logic [31:0] soc_cycles;
    logic [31:0] soc_cycles_final;
    logic soc_cycles_running;
    logic soc_cycles_captured;
    wire commit=req_i && wen_i && addr_i==15 && data_i==32'hb007c0de;
    wire reload=req_i && wen_i && addr_i==15 && data_i==0;
    wire cycle_start=(commit && loaded_words==2048) || PREINITIALIZED;
    wire test_status_write=sram_write_i && sram_be_i==4'hf &&
        sram_addr_i==32'h80001fe0 &&
        (sram_wdata_i==32'hc0dec0de || sram_wdata_i==32'hdeadbeef);
    always_ff @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) begin
            loaded_words<=PREINITIALIZED ? 12'd2048:12'd0;
            release_margin<=0;ready_o<=0;data_o<=0;
            soc_cycles<=0;soc_cycles_final<=0;
            soc_cycles_running<=0;soc_cycles_captured<=0;
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
            if(reload) begin
                loaded_words<=0;release_margin<=0;ready_o<=0;
                soc_cycles<=0;soc_cycles_final<=0;
                soc_cycles_running<=0;soc_cycles_captured<=0;
            end
            if(!soc_cycles_running && !soc_cycles_captured && cycle_start) begin
                soc_cycles_running<=1;
                soc_cycles<=32'd1;
            end else if(soc_cycles_running && !soc_cycles_captured) begin
                soc_cycles<=soc_cycles+1'b1;
                if(test_status_write) begin
                    soc_cycles_final<=soc_cycles+1'b1;
                    soc_cycles_running<=0;
                    soc_cycles_captured<=1;
                end
            end
            if(req_i && !wen_i) case(addr_i)
                0:data_o<=32'h800002b7; // lui t0,0x80000
                1:data_o<=32'h00028067; // jalr zero,0(t0)
                14:data_o<=soc_cycles_captured ? soc_cycles_final:soc_cycles;
                15:data_o<={18'd0,ready_o,1'b0,loaded_words};
                default:data_o<=32'h0000006f; // jal zero,0: safe trap loop
            endcase
        end
    end
endmodule
