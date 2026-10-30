`timescale 1ns/1ps
// Loader drives the Debug Module's SBA request boundary. All transactions
// traverse the real AXI adapter, crossbar and SRAM/Boot interfaces.
module tb_soc;
    reg clk=0,rst_n=0;
    always #5 clk=~clk;
    wire tdo;
    my_soc_top dut(.clk_i(clk),.rst_ni(rst_n),.tck_i(1'b0),.tms_i(1'b0),.td_i(1'b0),.td_o(tdo));
    reg load_req=0,load_we=0;
    reg [3:0] load_be=15;
    reg [31:0] load_addr=0,load_data=0;
    reg [31:0] image[0:2047];
    reg [31:0] magic=0;
    integer cycles=0,read_overlap=0,write_overlap=0;
    task sba_write(input reg [31:0] address,value,input reg [3:0] be);
        integer timeout;
        begin
            @(negedge clk);load_req=1;load_we=1;load_addr=address;load_data=value;load_be=be;timeout=0;
            @(posedge clk);
            while(!dut.dm_master_gnt && timeout<1000) begin @(posedge clk);timeout=timeout+1;end
            if(timeout>=1000) $fatal(1,"SBA grant timeout");
            @(negedge clk);load_req=0;
            timeout=0;
            while(!dut.dm_master_r_valid && timeout<1000) begin @(posedge clk);timeout=timeout+1;end
            if(timeout>=1000) $fatal(1,"SBA write response timeout");
            @(negedge clk);
        end
    endtask
    always @(posedge clk) begin
        if(dut.ndmreset_n && !dut.boot_ready && dut.instr_req) $fatal(1,"CPU fetched before firmware commit");
        if(dut.sram_req && dut.sram_we && dut.sram_addr==32'h80001fe0) magic<=dut.sram_wdata;
        if(dut.i_npu_subsystem.i_npu_core.core.product_valid && dut.dma_read_active) read_overlap<=read_overlap+1;
        if(dut.i_npu_subsystem.i_npu_core.core.product_valid && dut.dma_write_active) write_overlap<=write_overlap+1;
    end
    integer i;
    initial begin
        force dut.dm_master_req=load_req;force dut.dm_master_we=load_we;
        force dut.dm_master_add=load_addr;force dut.dm_master_wdata=load_data;force dut.dm_master_be=load_be;
        $readmemh("firmware.hex",image);
        #1;rst_n=0;repeat(4) @(negedge clk);#2;rst_n=1;
        repeat(7) @(posedge clk);
        #1;if(dut.ndmreset_n) $fatal(1,"System reset margin shorter than 8 clock edges");
        repeat(20) @(negedge clk);
        sba_write(32'h0001003c,32'hb007c0de,15);
        repeat(12) @(negedge clk);
        if(dut.boot_ready || dut.instr_req) $fatal(1,"Key alone started CPU");
        sba_write(32'h80001ffc,image[2047],15);
        sba_write(32'h80000000,image[0],3);
        if(dut.i_bootram.loaded_words!=0) $fatal(1,"Out-of-order/partial writes counted as a complete image");
        for(i=0;i<2048;i=i+1) begin
            sba_write(32'h80000000+i*4,image[i],15);
            if(i==31) begin
                sba_write(32'h0001003c,32'hb007c0de,15);
                if(dut.boot_ready) $fatal(1,"Partial firmware started CPU");
            end
        end
        if(dut.boot_ready) $fatal(1,"Full image needs explicit commit");
        sba_write(32'h0001003c,32'hdeadbeef,15);
        repeat(8) @(negedge clk);
        if(dut.boot_ready) $fatal(1,"Wrong key started CPU");
        sba_write(32'h0001003c,32'hb007c0de,15);
        while(cycles<200000 && magic!==32'hc0dec0de) begin
            @(negedge clk);cycles=cycles+1;
            if(magic===32'hdeadbeef) $fatal(1,"CPU numerical self-check failed");
        end
        if(magic!==32'hc0dec0de) $fatal(1,"SoC timeout, PC=%h",dut.instr_addr);
        if(read_overlap==0 || write_overlap==0) $fatal(1,"Full AXI SoC did not overlap DMA and MAC");
        if(dut.i_bootram.soc_cycles_final<=cycles ||
           ^dut.i_bootram.soc_cycles_final===1'bx)
            $fatal(1,"Invalid hardware SoC cycle count: %0d",dut.i_bootram.soc_cycles_final);
        $display("INT8_SOC PASS cycles=%0d hw_soc_cycles=%0d DMA_read_MAC_overlap=%0d DMA_write_MAC_overlap=%0d",
                 cycles,dut.i_bootram.soc_cycles_final,read_overlap,write_overlap);
        // Asynchronous reassertion must revoke execution immediately.
        #2;rst_n=0;#1;
        if(dut.ndmreset_n || dut.boot_ready) $fatal(1,"Reset assertion failed");
        $finish;
    end
endmodule
