`timescale 1ns/1ps
// Read-path probe: prints the per-cycle state of the instruction-fetch read
// path (adapter -> xbar -> axi2mem -> SRAM) so the extra cycle can be located.
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
    integer cycles=0;
    integer win=0;
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
    always @(posedge clk) if(dut.sram_req && dut.sram_we && dut.sram_addr==32'h80001fe0) magic<=dut.sram_wdata;
    // per-cycle window dump once the CPU starts fetching
    always @(posedge clk) if(win>0) begin
        $display("R%0d cpu req=%b gnt=%b rv=%b pc=%h ad=%0d | s1 arv=%b arr=%b rv=%b rr=%b | a2m=%0d sramreq=%b pq=%b | rdata=%h",
                 win,dut.instr_req,dut.instr_gnt,dut.instr_rvalid,dut.instr_addr,
                 dut.i_axi_adapter_instr.state_q,
                 dut.slave[1].ar_valid,dut.slave[1].ar_ready,dut.slave[1].r_valid,dut.slave[1].r_ready,
                 dut.i_axi2sram.state_q,dut.sram_req,dut.i_mainmem.port_req_q,dut.instr_rdata);
        win=win+1;
        if(win>14) win=0;
    end
    integer k;
    initial begin
        force dut.dm_master_req=load_req;force dut.dm_master_we=load_we;
        force dut.dm_master_add=load_addr;force dut.dm_master_wdata=load_data;force dut.dm_master_be=load_be;
        $readmemh("firmware.hex",image);
        #1;rst_n=0;repeat(4) @(negedge clk);#2;rst_n=1;
        repeat(7) @(posedge clk);
        repeat(20) @(negedge clk);
        sba_write(32'h0001003c,32'hb007c0de,15);
        repeat(12) @(negedge clk);
        sba_write(32'h80001ffc,image[2047],15);
        sba_write(32'h80000000,image[0],3);
        for(k=0;k<2048;k=k+1) sba_write(32'h80000000+k*4,image[k],15);
        sba_write(32'h0001003c,32'hb007c0de,15);
        @(negedge clk);
        @(posedge clk); while(!dut.instr_req) @(posedge clk);
        win=1;
        while(cycles<200000 && magic!==32'hc0dec0de) begin
            @(negedge clk);cycles=cycles+1;
            if(magic===32'hdeadbeef) $fatal(1,"CPU numerical self-check failed");
        end
        if(magic!==32'hc0dec0de) $fatal(1,"SoC timeout");
        $display("INT8_SOC PASS cycles=%0d time_ns=%0.3f",cycles,$realtime);
        $finish;
    end
endmodule
