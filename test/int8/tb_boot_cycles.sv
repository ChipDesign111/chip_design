`timescale 1ns/1ps

module tb_boot_cycles;
    reg clk=0,rst_n=0,req=0,wen=0;
    reg [3:0] addr=0,sram_be=0;
    reg [31:0] data=0;
    reg sram_write=0;
    reg [31:0] sram_addr=0,sram_wdata=0;
    reg firmware_fetch=0;
    wire ready;
    wire [31:0] data_o;
    reg [31:0] cycles_before,cycles_first,cycles_frozen;

    always #5 clk=~clk;

    bootram #(.PREINITIALIZED(1)) dut (
        .clk_i(clk),.rst_ni(rst_n),.req_i(req),.wen_i(wen),
        .addr_i(addr),.data_i(data),
        .sram_write_i(sram_write),.sram_addr_i(sram_addr),
        .sram_be_i(sram_be),.sram_wdata_i(sram_wdata),
        .firmware_fetch_i(firmware_fetch),
        .ready_o(ready),.data_o(data_o)
    );

    task boot_read(input [3:0] read_addr,output [31:0] value);
        begin
            @(negedge clk);
            req=1;wen=0;addr=read_addr;
            @(posedge clk);
            @(negedge clk);
            value=data_o;req=0;
        end
    endtask

    initial begin
        #1;repeat(3) @(negedge clk);rst_n=1;
        repeat(20) @(negedge clk);

        if(!ready) $fatal(1,"Preinitialized boot did not become ready");
        boot_read(14,cycles_before);
        if(cycles_before!==32'd0)
            $fatal(1,"Counter started while CPU was still halted: %0d",cycles_before);

        // Keep the CPU "halted" after readiness. This must not consume cycles.
        repeat(2000) @(negedge clk);
        boot_read(14,cycles_before);
        if(cycles_before!==32'd0)
            $fatal(1,"Debug-halt time leaked into cycle count: %0d",cycles_before);

        @(negedge clk);firmware_fetch=1;
        @(negedge clk);firmware_fetch=0;
        repeat(20) @(negedge clk);

        @(negedge clk);
        sram_write=1;sram_addr=32'h80001fe0;sram_be=4'hf;sram_wdata=32'hc0dec0de;
        @(posedge clk);
        @(negedge clk);sram_write=0;

        boot_read(14,cycles_first);
        if(cycles_first<=0 || cycles_first>32)
            $fatal(1,"Unexpected first-fetch cycle count: %0d",cycles_first);
        repeat(50) @(negedge clk);
        boot_read(14,cycles_frozen);
        if(cycles_frozen!==cycles_first)
            $fatal(1,"Cycle count did not freeze: %0d -> %0d",cycles_first,cycles_frozen);

        $display("BOOT_CYCLES PASS pre_fetch=%0d captured=%0d frozen=%0d",
                 cycles_before,cycles_first,cycles_frozen);
        $finish;
    end
endmodule
