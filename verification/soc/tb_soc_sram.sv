`timescale 1ns/1ps
// SRAM simulation loader and passive CPU-write completion monitor.
module tb_soc_sram #(
    parameter INIT_FILE = ""
);
    reg clk_i = 0, rst_ni = 0;
    wire td_o;
    always #5 clk_i = ~clk_i;
    my_soc_top dut (.clk_i(clk_i), .rst_ni(rst_ni),
        .tck_i(1'b0), .tms_i(1'b0), .td_i(1'b0), .td_o(td_o));
    reg [31:0] image [0:2047];
    reg load_req = 0;
    reg [31:0] load_addr = 0, load_data = 0;
    reg [31:0] magic_status = 0;
    integer cycle_count = 0;

    // Observe real CPU/AXI writes; never inject a completion status.
    always @(posedge clk_i) begin
        if (rst_ni && dut.sram_req && dut.sram_we &&
            dut.sram_addr == 32'h80001fe0)
            for (integer b = 0; b < 4; b = b + 1)
                if (dut.sram_be[b])
                    magic_status[b*8 +: 8] <= dut.sram_wdata[b*8 +: 8];
    end

    initial begin
        if (INIT_FILE == "") $fatal(1, "Missing SRAM firmware image");
        for (integer i = 0; i < 2048; i = i + 1) image[i] = 0;
        $readmemh(INIT_FILE, image);
        // Testbench-only program preload through actual memory ports while CPU
        // reset is asserted. No reference to a vendor's internal memory array.
        force dut.i_mainmem.req_i = load_req;
        force dut.i_mainmem.we_i = 1'b1;
        force dut.i_mainmem.be_i = 4'hf;
        force dut.i_mainmem.addr_i = load_addr;
        force dut.i_mainmem.wdata_i = load_data;
        for (integer i = 0; i < 2048; i = i + 1) begin
            @(negedge clk_i);
            load_req = 1; load_addr = 32'h80000000 + i*4; load_data = image[i];
            @(posedge clk_i); #2;
        end
        @(negedge clk_i);
        load_req = 0;
        release dut.i_mainmem.req_i;
        release dut.i_mainmem.we_i;
        release dut.i_mainmem.be_i;
        release dut.i_mainmem.addr_i;
        release dut.i_mainmem.wdata_i;
        repeat (8) @(negedge clk_i);
        rst_ni = 1;
        while (cycle_count < 1000000) begin
            @(posedge clk_i); #2;
            cycle_count = cycle_count + 1;
            if (magic_status === 32'hc0dec0de) begin
                $display("PASS: SRAM SoC self-check OK after %0d cycles", cycle_count);
                $finish;
            end
            if (magic_status === 32'hdeadbeef) $fatal(1, "CPU self-check failed");
        end
        $fatal(1, "SRAM SoC timeout");
    end
endmodule
