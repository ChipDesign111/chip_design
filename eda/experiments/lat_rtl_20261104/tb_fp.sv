`timescale 1ns/1ps
// Fetch-buffer profiler: same serial loader as tb_serial, plus counters for
// instruction-port hits, stall cycles and burst fills.
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
    integer cycles=0, profiling=0;
    integer c_total=0,c_stall=0,c_gnt=0,c_fill=0,c_pf=0,c_miss=0;
    reg ar_prev=0;
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
    always @(posedge clk) if(profiling) begin
        c_total=c_total+1;
        if(dut.instr_gnt) c_gnt=c_gnt+1;
        if(dut.instr_req && !dut.instr_gnt) c_stall=c_stall+1;
        if(dut.i_ifetch.axi_req_o.ar_valid && !ar_prev) begin
            c_fill=c_fill+1;
            if(dut.i_ifetch.start_miss) c_miss=c_miss+1; else c_pf=c_pf+1;
        end
        ar_prev=dut.i_ifetch.axi_req_o.ar_valid;
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
        ar_prev=dut.i_ifetch.axi_req_o.ar_valid;
        profiling=1;
        while(c_total<200000 && magic!==32'hc0dec0de) begin
            @(negedge clk);cycles=cycles+1;
            if(magic===32'hdeadbeef) $fatal(1,"CPU numerical self-check failed");
        end
        profiling=0;
        if(magic!==32'hc0dec0de) $fatal(1,"SoC timeout, PC=%h",dut.instr_addr);
        $display("FPROF cycles=%0d grants=%0d stall=%0d fills=%0d (miss=%0d pf=%0d)",
                 c_total,c_gnt,c_stall,c_fill,c_miss,c_pf);
        $display("INT8_SOC PASS cycles=%0d time_ns=%0.3f",cycles,$realtime);
        $finish;
    end
endmodule
