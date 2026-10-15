`timescale 1ns/1ps
module tb_mainmem_sram;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0, req = 0, we = 0;
    reg [3:0] be = 0;
    reg [31:0] addr = 0, data = 0;
    wire [31:0] result;
    reg [31:0] gold [0:2047];
    reg [31:0] rng = 32'h5a17c0de;
    integer reads = 0, writes = 0;
    integer i, mask;
    my_mainmem dut (.clk_i(clk), .rst_ni(rst_n), .req_i(req),
        .we_i(we), .be_i(be), .addr_i(addr), .wdata_i(data), .rdata_o(result));

    function automatic [31:0] random_word(input [31:0] value);
        reg [31:0] x;
        x = value ^ (value << 13);
        x = x ^ (x >> 17);
        return x ^ (x << 5);
    endfunction

    task automatic write_word(input integer index, input [31:0] value,
                              input [3:0] mask, input bit enabled);
        integer b;
        @(negedge clk);
        req = enabled; we = 1; be = mask;
        addr = 32'h80000000 + index*4; data = value;
        @(posedge clk); #2;
        if (enabled) begin
            for (b = 0; b < 4; b = b + 1)
                if (mask[b]) gold[index][b*8 +: 8] = value[b*8 +: 8];
            writes = writes + 1;
        end
    endtask

    task automatic read_word(input integer index, input [3:0] read_be);
        reg prior_read;
        reg [31:0] prior_value;
        @(negedge clk);
        prior_read = req && !we;
        prior_value = result;
        req = 1; we = 0; be = read_be;
        addr = 32'h80000000 + index*4;
        #1;
        if (prior_read && result !== prior_value)
            $fatal(1, "SRAM output changed before sampling clock");
        @(posedge clk); #2;
        if (result !== gold[index])
            $fatal(1, "SRAM mismatch word=%0d got=%h expected=%h", index, result, gold[index]);
        reads = reads + 1;
    endtask

    initial begin
        // Cover every address, including 0 and 2047; initialize only via writes.
        for (i = 0; i < 2048; i = i + 1)
            write_word(i, 32'h31415926 ^ (i*32'h10204081), 4'hf, 1);
        rst_n = 1;
        for (i = 0; i < 2048; i = i + 1) read_word(i, 4'hf);
        // All byte masks, disabled writes and nonzero BE on a read.
        for (mask = 0; mask < 16; mask = mask + 1) begin
            write_word(0, 32'hdeadbeef ^ mask, mask, 1);
            read_word(0, mask);
            write_word(0, 32'hffffffff, mask, 0);
            read_word(0, 4'hf);
        end
        // Deterministic random reads immediately after masked writes.
        for (i = 0; i < 2000; i = i + 1) begin
            rng = random_word(rng);
            write_word(rng[10:0], rng ^ 32'hac00d123, rng[14:11], 1);
            read_word(rng[10:0], 4'hf);
        end
        @(negedge clk); req = 0; rst_n = 0;
        repeat (3) @(posedge clk);
        rst_n = 1;
        for (i = 0; i < 2048; i = i + 1) read_word(i, 4'h0);
        $display("SRAM_UNIT PASS reads=%0d writes=%0d masks=16", reads, writes);
        $finish;
    end
    initial begin #200000; $fatal(1, "SRAM unit timeout"); end
endmodule
