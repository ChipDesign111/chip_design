`timescale 1ns/1ps
// Load a complete 8 KiB image through Debug SBA, then let the real CPU pack
// weights, launch RAW tiles, reduce partial sums, and verify every layer.
module tb_generic_soc;
    reg clk=0,rst_n=0;
    always #5 clk=~clk;
    wire tdo;
    my_soc_top dut(.clk_i(clk),.rst_ni(rst_n),.tck_i(1'b0),.tms_i(1'b0),.td_i(1'b0),.td_o(tdo));
    reg load_req=0,load_we=0;
    reg [3:0] load_be=15;
    reg [31:0] load_addr=0,load_data=0;
    reg [31:0] image[0:2047];
    reg [31:0] magic=0;
    integer cycles=0,tiles=0,expected_tiles,i;
    task sba_write(input reg [31:0] address,value);
        integer timeout;
        begin
            @(negedge clk);load_req=1;load_we=1;load_addr=address;load_data=value;
            @(posedge clk);timeout=0;
            while(!dut.dm_master_gnt && timeout<1000) begin @(posedge clk);timeout=timeout+1;end
            if(timeout>=1000) $fatal(1,"SBA grant timeout");
            @(negedge clk);load_req=0;timeout=0;
            while(!dut.dm_master_r_valid && timeout<1000) begin @(posedge clk);timeout=timeout+1;end
            if(timeout>=1000) $fatal(1,"SBA response timeout");
            @(negedge clk);
        end
    endtask
    always @(posedge clk) begin
        if(dut.ndmreset_n && !dut.boot_ready && dut.instr_req)
            $fatal(1,"CPU fetched before image commit");
        if(dut.sram_req && dut.sram_we && dut.sram_addr==32'h80001fe0)
            magic<=dut.sram_wdata;
        if(dut.i_npu_subsystem.i_npu_core.start) begin
            if(!dut.i_npu_subsystem.i_npu_core.raw_mode)
                $fatal(1,"Generic firmware accidentally launched legacy mode");
            tiles<=tiles+1;
        end
        if(dut.npu_busy && dut.i_npu_subsystem.i_npu_core.layer)
            $fatal(1,"RAW kernel executed FC2");
        if(dut.auto_start &&
           (dut.auto_source<32'h800017c0 || dut.auto_source>=32'h80001fc0 || dut.auto_words!=16))
            $fatal(1,"Unexpected RAW DMA descriptor or W2 prefetch");
    end
    initial begin
        if(!$value$plusargs("TILES=%d",expected_tiles)) $fatal(1,"TILES required");
        force dut.dm_master_req=load_req;force dut.dm_master_we=load_we;
        force dut.dm_master_add=load_addr;force dut.dm_master_wdata=load_data;force dut.dm_master_be=load_be;
        $readmemh("firmware.hex",image);
        #1;rst_n=0;repeat(4) @(negedge clk);#2;rst_n=1;
        repeat(30) @(negedge clk);
        for(i=0;i<2048;i=i+1) sba_write(32'h80000000+i*4,image[i]);
        sba_write(32'h0001003c,32'hb007c0de);
        while(cycles<2000000 && magic!==32'hc0dec0de) begin
            @(negedge clk);cycles=cycles+1;
            if(magic===32'hdeadbeef)
                $fatal(1,"Generic CPU self-check failed PC=%h tiles=%0d",dut.instr_addr,tiles);
        end
        if(magic!==32'hc0dec0de) $fatal(1,"Generic CPU timeout PC=%h tiles=%0d",dut.instr_addr,tiles);
        if(tiles!=expected_tiles) $fatal(1,"Expected %0d tiles, got %0d",expected_tiles,tiles);
        if(dut.i_npu_subsystem.i_npu_core.raw_mode)
            $fatal(1,"CPU failed to restore legacy MODE=0");
        if(dut.i_npu_subsystem.i_npu_core.core.fc1_cycles!=128 ||
           dut.i_npu_subsystem.i_npu_core.core.fc2_cycles!=0)
            $fatal(1,"Generic tile issue counters are incorrect");
        $display("GENERIC_SOC_PASS cycles=%0d tiles=%0d",cycles,tiles);
        $finish;
    end
endmodule
