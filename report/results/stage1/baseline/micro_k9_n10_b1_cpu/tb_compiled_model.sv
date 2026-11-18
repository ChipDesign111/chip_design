`timescale 1ns/1ps
// Loader drives the Debug Module's SBA request boundary. All transactions
// traverse the real AXI adapter, crossbar and SRAM/Boot interfaces.
module tb_compiled_model;
    reg clk=0,rst_n=0;
    always #5 clk=~clk;
    wire tdo;
    my_soc_top dut(.clk_i(clk),.rst_ni(rst_n),.tck_i(1'b0),.tms_i(1'b0),.td_i(1'b0),.td_o(tdo));
    reg load_req=0,load_we=0;
    reg [3:0] load_be=15;
    reg [31:0] load_addr=0,load_data=0;
    reg [31:0] image[0:2047];
    reg [31:0] magic=0;
    reg fetch_started=0;
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
        if(dut.boot_ready && !dut.firmware_fetch_start && !fetch_started &&
           dut.i_bootram.soc_cycles!==32'd0)
            $fatal(1,"SoC cycle counter started before first firmware fetch");
        // Match bootram.cycle_start: a raw request in the uninitialised
        // power-on interval is not a committed firmware fetch.
        if(dut.ndmreset_n===1'b1 && dut.boot_ready===1'b1 &&
           dut.firmware_fetch_start && !fetch_started) begin
            if(dut.i_bootram.soc_cycles!==32'd0)
                $fatal(1,"SoC cycle counter did not start at first firmware fetch");
            fetch_started<=1;
        end
        if(dut.sram_req && dut.sram_we && dut.sram_addr==32'h80001fe0) magic<=dut.sram_wdata;
        if(dut.i_npu_subsystem.i_npu_core.core.product_valid && dut.dma_read_active) read_overlap<=read_overlap+1;
        if(dut.i_npu_subsystem.i_npu_core.core.product_valid && dut.dma_write_active) write_overlap<=write_overlap+1;
    end

    reg [31:0] observed;
    integer npu_starts=0,npu_issue=0,result_fd;
    always @(posedge clk) begin
        if(dut.i_npu_subsystem.i_npu_core.start) npu_starts<=npu_starts+1;
        if(dut.i_npu_subsystem.i_npu_core.core.product_valid) npu_issue<=npu_issue+1;
    end
    task sba_read(input reg [31:0] address,output reg [31:0] value);
        integer timeout;
        begin
            @(negedge clk);load_req=1;load_we=0;load_addr=address;load_be=15;timeout=0;
            @(posedge clk);
            while(!dut.dm_master_gnt && timeout<1000) begin @(posedge clk);timeout=timeout+1;end
            if(timeout>=1000) $fatal(1,"SBA read grant timeout");
            @(negedge clk);load_req=0;timeout=0;
            while(!dut.dm_master_r_valid && timeout<1000) begin @(posedge clk);timeout=timeout+1;end
            if(timeout>=1000) $fatal(1,"SBA read response timeout");
            value=dut.dm_master_r_rdata;
            @(negedge clk);
        end
    endtask


    integer profile_fd,profile_tick=0;
    reg profile_active=0,profile_finished=0;
    initial begin
        profile_fd=$fopen("profile.csv","w");
        if(profile_fd==0) $fatal(1,"Cannot open passive profile");
        $fdisplay(profile_fd,"tick,pc,busy,state,tile_ready,dma_busy,dma_r,dma_w,cpu_accept,cpu_we,cpu_addr,cpu_be,mem_req,mem_we,mem_addr,mem_be,start,k,n,batch,issued,dma_wait");
    end
    always @(posedge clk) begin
        profile_tick=profile_tick+1;
        if(dut.ndmreset_n===1'b1 && dut.boot_ready===1'b1 && dut.firmware_fetch_start)
            profile_active=1;
        if(profile_active && !profile_finished) begin
            $fdisplay(profile_fd,"%0d,%h,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%h,%h,%0d,%0d,%h,%h,%0d,%0d,%0d,%0d,%0d,%0d",
                profile_tick,dut.i_cpu.core_i.pc_id,
                dut.i_npu_subsystem.i_npu_core.core.busy,
                dut.i_npu_subsystem.i_npu_core.core.state,
                dut.i_npu_subsystem.i_npu_core.core.tile_valid_i,
                dut.dma_busy,dut.dma_read_active,dut.dma_write_active,
                dut.data_req && dut.data_gnt,dut.data_we,dut.data_addr,dut.data_be,
                dut.sram_req,dut.sram_we,dut.sram_addr,dut.sram_be,
                dut.i_npu_subsystem.i_npu_core.start,
                dut.i_npu_subsystem.i_npu_core.fc_k,
                dut.i_npu_subsystem.i_npu_core.fc_n,
                dut.i_npu_subsystem.i_npu_core.batch_count,
                dut.i_cpu.core_i.id_valid && dut.i_cpu.core_i.is_decoding,
                {dut.i_dma.i_engine.b_ready_o && !dut.i_dma.i_engine.b_valid_i,
                 dut.i_dma.i_engine.w_valid_o && !dut.i_dma.i_engine.w_ready_i,
                 dut.i_dma.i_engine.aw_valid_o && !dut.i_dma.i_engine.aw_ready_i,
                 dut.i_dma.i_engine.r_ready_o && !dut.i_dma.i_engine.r_valid_i,
                 dut.i_dma.i_engine.ar_valid_o && !dut.i_dma.i_engine.ar_ready_i});
            if(dut.sram_req && dut.sram_we && dut.sram_addr==32'h80001fe0 &&
               dut.sram_wdata==32'hc0dec0de) begin
                profile_finished=1;$fclose(profile_fd);
            end
        end
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
        if(!fetch_started) $fatal(1,"Firmware boot fetch was not observed");
        if(npu_starts!=0) $fatal(1,"Wrong NPU job count %0d",npu_starts);
        if(!dut.i_bootram.soc_cycles_captured ||
           dut.i_bootram.soc_cycles<=0 ||
           dut.i_bootram.soc_cycles>=cycles ||
           ^dut.i_bootram.soc_cycles===1'bx)
            $fatal(1,"Invalid hardware SoC cycle count: %0d",dut.i_bootram.soc_cycles);
result_fd=$fopen("actual_tensors.hex","w"); if(result_fd==0) $fatal(1,"Cannot open tensor dump");
sba_read(32'h80001fb4,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001fb4,observed);
if(observed!==32'h7fecdeb5) $fatal(1,"Tensor input_1 row 0 word 0 mismatch actual %h",observed);
sba_read(32'h80001fb8,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001fb8,observed);
if(observed!==32'h7398b414) $fatal(1,"Tensor input_1 row 0 word 1 mismatch actual %h",observed);
sba_read(32'h80001fbc,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001fbc,observed);
if(observed!==32'h00000062) $fatal(1,"Tensor input_1 row 0 word 2 mismatch actual %h",observed);
sba_read(32'h80001fa8,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001fa8,observed);
if(observed!==32'he25f28f7) $fatal(1,"Tensor _0 row 0 word 0 mismatch actual %h",observed);
sba_read(32'h80001fac,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001fac,observed);
if(observed!==32'h0b81a389) $fatal(1,"Tensor _0 row 0 word 1 mismatch actual %h",observed);
sba_read(32'h80001fb0,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001fb0,observed);
if(observed!==32'h00002c1f) $fatal(1,"Tensor _0 row 0 word 2 mismatch actual %h",observed);
$fclose(result_fd);
        $display("INT8_SOC PASS cycles=%0d hw_soc_cycles=%0d npu_cycles=%0d fc1_issue_cycles=%0d fc2_issue_cycles=%0d DMA_read_MAC_overlap=%0d DMA_write_MAC_overlap=%0d",
                 cycles,dut.i_bootram.soc_cycles,
                 dut.i_npu_subsystem.i_npu_core.core.cycle_count,
                 dut.i_npu_subsystem.i_npu_core.core.fc1_cycles,
                 dut.i_npu_subsystem.i_npu_core.core.fc2_cycles,
                 read_overlap,write_overlap);
        // Two falling request samples followed by the rising retiming edge.
        #2;rst_n=0;repeat(2) @(negedge clk);@(posedge clk);#1;
        if(dut.ndmreset_n || dut.boot_ready) $fatal(1,"Reset assertion failed");
        $display("COMPILED_MODEL_PASS npu_jobs=%0d npu_issue=%0d",npu_starts,npu_issue);
        $finish;
    end
endmodule
