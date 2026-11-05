`timescale 1ns/1ps
// Fetch-path profiler: measures instruction-fetch issue rate and the
// grant->rvalid latency, split by whether the DMA was using the fabric.
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
    integer c_total=0,c_istall=0,c_dstall=0,c_npubusy=0,c_dma=0,c_idle=0;
    integer fetches=0, lat_sum=0, lat_max=0, lat_fetch=0;
    integer datareqs=0, dlat_sum=0;
    integer istall_dma=0, istall_nodma=0;
    reg fetch_pending=0;
    reg [31:0] last_fetch_addr=0;
    integer seq_fetches=0, nonseq_fetches=0;
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
        if(dut.instr_req && !dut.instr_gnt) begin
            c_istall=c_istall+1;
            if(dut.dma_read_active || dut.dma_write_active) istall_dma=istall_dma+1;
            else istall_nodma=istall_nodma+1;
        end
        if(dut.data_req  && !dut.data_gnt)  c_dstall=c_dstall+1;
        if(dut.i_npu_subsystem.i_npu_core.busy) c_npubusy=c_npubusy+1;
        if(dut.dma_read_active || dut.dma_write_active) c_dma=c_dma+1;
        // fetch issue
        if(dut.instr_req && dut.instr_gnt) begin
            fetches=fetches+1;
            fetch_pending=1; lat_fetch=0;
            if(dut.instr_addr==last_fetch_addr+4) seq_fetches=seq_fetches+1;
            else nonseq_fetches=nonseq_fetches+1;
            last_fetch_addr=dut.instr_addr;
        end
        if(fetch_pending) begin
            lat_fetch=lat_fetch+1;
            if(dut.instr_rvalid) begin
                lat_sum=lat_sum+lat_fetch;
                if(lat_fetch>lat_max) lat_max=lat_fetch;
                fetch_pending=0;
            end
        end
        if(dut.data_req && dut.data_gnt) datareqs=datareqs+1;
        if(!dut.instr_req && !dut.data_req) c_idle=c_idle+1;
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
        profiling=1;
        while(c_total<200000 && magic!==32'hc0dec0de) begin
            @(negedge clk);cycles=cycles+1;
            if(magic===32'hdeadbeef) $fatal(1,"CPU numerical self-check failed");
        end
        profiling=0;
        if(magic!==32'hc0dec0de) $fatal(1,"SoC timeout, PC=%h",dut.instr_addr);
        $display("PROFILE2 cycles=%0d fetches=%0d data_reqs=%0d avg_fetch_lat=%0d max=%0d seq=%0d nonseq=%0d",
                 c_total,fetches,datareqs,(fetches>0?lat_sum/fetches:0),lat_max,seq_fetches,nonseq_fetches);
        $display("PROFILE2 instr_stall=%0d (dma=%0d nodma=%0d) data_stall=%0d npu_busy=%0d dma_active=%0d no_req=%0d",
                 c_istall,istall_dma,istall_nodma,c_dstall,c_npubusy,c_dma,c_idle);
        $display("INT8_SOC PASS cycles=%0d time_ns=%0.3f",cycles,$realtime);
        $finish;
    end
endmodule
