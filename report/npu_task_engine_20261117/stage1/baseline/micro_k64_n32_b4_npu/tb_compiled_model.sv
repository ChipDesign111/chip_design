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
        if(npu_starts!=1) $fatal(1,"Wrong NPU job count %0d",npu_starts);
        if(!dut.i_bootram.soc_cycles_captured ||
           dut.i_bootram.soc_cycles<=0 ||
           dut.i_bootram.soc_cycles>=cycles ||
           ^dut.i_bootram.soc_cycles===1'bx)
            $fatal(1,"Invalid hardware SoC cycle count: %0d",dut.i_bootram.soc_cycles);
result_fd=$fopen("actual_tensors.hex","w"); if(result_fd==0) $fatal(1,"Cannot open tensor dump");
sba_read(32'h80001ec0,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ec0,observed);
if(observed!==32'hb67758ed) $fatal(1,"Tensor input_1 row 0 word 0 mismatch actual %h",observed);
sba_read(32'h80001ec4,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ec4,observed);
if(observed!==32'h40cc55c3) $fatal(1,"Tensor input_1 row 0 word 1 mismatch actual %h",observed);
sba_read(32'h80001ec8,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ec8,observed);
if(observed!==32'h71185a6d) $fatal(1,"Tensor input_1 row 0 word 2 mismatch actual %h",observed);
sba_read(32'h80001ecc,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ecc,observed);
if(observed!==32'ha571bc38) $fatal(1,"Tensor input_1 row 0 word 3 mismatch actual %h",observed);
sba_read(32'h80001ed0,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ed0,observed);
if(observed!==32'h73e5151a) $fatal(1,"Tensor input_1 row 0 word 4 mismatch actual %h",observed);
sba_read(32'h80001ed4,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ed4,observed);
if(observed!==32'h148af863) $fatal(1,"Tensor input_1 row 0 word 5 mismatch actual %h",observed);
sba_read(32'h80001ed8,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ed8,observed);
if(observed!==32'h892235c8) $fatal(1,"Tensor input_1 row 0 word 6 mismatch actual %h",observed);
sba_read(32'h80001edc,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001edc,observed);
if(observed!==32'h08f62935) $fatal(1,"Tensor input_1 row 0 word 7 mismatch actual %h",observed);
sba_read(32'h80001ee0,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ee0,observed);
if(observed!==32'h99b28ffd) $fatal(1,"Tensor input_1 row 0 word 8 mismatch actual %h",observed);
sba_read(32'h80001ee4,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ee4,observed);
if(observed!==32'h98155599) $fatal(1,"Tensor input_1 row 0 word 9 mismatch actual %h",observed);
sba_read(32'h80001ee8,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ee8,observed);
if(observed!==32'h485fb988) $fatal(1,"Tensor input_1 row 0 word 10 mismatch actual %h",observed);
sba_read(32'h80001eec,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001eec,observed);
if(observed!==32'he7b1eb63) $fatal(1,"Tensor input_1 row 0 word 11 mismatch actual %h",observed);
sba_read(32'h80001ef0,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ef0,observed);
if(observed!==32'hca37f8c4) $fatal(1,"Tensor input_1 row 0 word 12 mismatch actual %h",observed);
sba_read(32'h80001ef4,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ef4,observed);
if(observed!==32'h7fa71c52) $fatal(1,"Tensor input_1 row 0 word 13 mismatch actual %h",observed);
sba_read(32'h80001ef8,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ef8,observed);
if(observed!==32'h3ce13e9e) $fatal(1,"Tensor input_1 row 0 word 14 mismatch actual %h",observed);
sba_read(32'h80001efc,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001efc,observed);
if(observed!==32'he7412d52) $fatal(1,"Tensor input_1 row 0 word 15 mismatch actual %h",observed);
sba_read(32'h80001f00,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f00,observed);
if(observed!==32'h94d8b762) $fatal(1,"Tensor input_1 row 1 word 0 mismatch actual %h",observed);
sba_read(32'h80001f04,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f04,observed);
if(observed!==32'hadd38586) $fatal(1,"Tensor input_1 row 1 word 1 mismatch actual %h",observed);
sba_read(32'h80001f08,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f08,observed);
if(observed!==32'h3cab02e6) $fatal(1,"Tensor input_1 row 1 word 2 mismatch actual %h",observed);
sba_read(32'h80001f0c,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f0c,observed);
if(observed!==32'h89c477ad) $fatal(1,"Tensor input_1 row 1 word 3 mismatch actual %h",observed);
sba_read(32'h80001f10,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f10,observed);
if(observed!==32'h9adc589b) $fatal(1,"Tensor input_1 row 1 word 4 mismatch actual %h",observed);
sba_read(32'h80001f14,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f14,observed);
if(observed!==32'haf267777) $fatal(1,"Tensor input_1 row 1 word 5 mismatch actual %h",observed);
sba_read(32'h80001f18,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f18,observed);
if(observed!==32'hb6268b7b) $fatal(1,"Tensor input_1 row 1 word 6 mismatch actual %h",observed);
sba_read(32'h80001f1c,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f1c,observed);
if(observed!==32'h64e1a7c2) $fatal(1,"Tensor input_1 row 1 word 7 mismatch actual %h",observed);
sba_read(32'h80001f20,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f20,observed);
if(observed!==32'h207194b4) $fatal(1,"Tensor input_1 row 1 word 8 mismatch actual %h",observed);
sba_read(32'h80001f24,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f24,observed);
if(observed!==32'h351289b1) $fatal(1,"Tensor input_1 row 1 word 9 mismatch actual %h",observed);
sba_read(32'h80001f28,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f28,observed);
if(observed!==32'h200aff6e) $fatal(1,"Tensor input_1 row 1 word 10 mismatch actual %h",observed);
sba_read(32'h80001f2c,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f2c,observed);
if(observed!==32'ha238bc7c) $fatal(1,"Tensor input_1 row 1 word 11 mismatch actual %h",observed);
sba_read(32'h80001f30,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f30,observed);
if(observed!==32'heba38662) $fatal(1,"Tensor input_1 row 1 word 12 mismatch actual %h",observed);
sba_read(32'h80001f34,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f34,observed);
if(observed!==32'h362242fa) $fatal(1,"Tensor input_1 row 1 word 13 mismatch actual %h",observed);
sba_read(32'h80001f38,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f38,observed);
if(observed!==32'hb68c9579) $fatal(1,"Tensor input_1 row 1 word 14 mismatch actual %h",observed);
sba_read(32'h80001f3c,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f3c,observed);
if(observed!==32'h602dd71a) $fatal(1,"Tensor input_1 row 1 word 15 mismatch actual %h",observed);
sba_read(32'h80001f40,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f40,observed);
if(observed!==32'hc8e00b86) $fatal(1,"Tensor input_1 row 2 word 0 mismatch actual %h",observed);
sba_read(32'h80001f44,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f44,observed);
if(observed!==32'h20affbe2) $fatal(1,"Tensor input_1 row 2 word 1 mismatch actual %h",observed);
sba_read(32'h80001f48,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f48,observed);
if(observed!==32'hf16eab51) $fatal(1,"Tensor input_1 row 2 word 2 mismatch actual %h",observed);
sba_read(32'h80001f4c,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f4c,observed);
if(observed!==32'h5c55f318) $fatal(1,"Tensor input_1 row 2 word 3 mismatch actual %h",observed);
sba_read(32'h80001f50,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f50,observed);
if(observed!==32'hf9af9134) $fatal(1,"Tensor input_1 row 2 word 4 mismatch actual %h",observed);
sba_read(32'h80001f54,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f54,observed);
if(observed!==32'h1f66af2b) $fatal(1,"Tensor input_1 row 2 word 5 mismatch actual %h",observed);
sba_read(32'h80001f58,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f58,observed);
if(observed!==32'h7d6753d3) $fatal(1,"Tensor input_1 row 2 word 6 mismatch actual %h",observed);
sba_read(32'h80001f5c,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f5c,observed);
if(observed!==32'h1e3ce9af) $fatal(1,"Tensor input_1 row 2 word 7 mismatch actual %h",observed);
sba_read(32'h80001f60,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f60,observed);
if(observed!==32'h014dea38) $fatal(1,"Tensor input_1 row 2 word 8 mismatch actual %h",observed);
sba_read(32'h80001f64,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f64,observed);
if(observed!==32'h9faff552) $fatal(1,"Tensor input_1 row 2 word 9 mismatch actual %h",observed);
sba_read(32'h80001f68,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f68,observed);
if(observed!==32'hdf7f17de) $fatal(1,"Tensor input_1 row 2 word 10 mismatch actual %h",observed);
sba_read(32'h80001f6c,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f6c,observed);
if(observed!==32'hd80b3bb7) $fatal(1,"Tensor input_1 row 2 word 11 mismatch actual %h",observed);
sba_read(32'h80001f70,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f70,observed);
if(observed!==32'he494ea8d) $fatal(1,"Tensor input_1 row 2 word 12 mismatch actual %h",observed);
sba_read(32'h80001f74,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f74,observed);
if(observed!==32'h071fb51b) $fatal(1,"Tensor input_1 row 2 word 13 mismatch actual %h",observed);
sba_read(32'h80001f78,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f78,observed);
if(observed!==32'hcf8bacf3) $fatal(1,"Tensor input_1 row 2 word 14 mismatch actual %h",observed);
sba_read(32'h80001f7c,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f7c,observed);
if(observed!==32'haba553c0) $fatal(1,"Tensor input_1 row 2 word 15 mismatch actual %h",observed);
sba_read(32'h80001f80,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f80,observed);
if(observed!==32'hacb383fe) $fatal(1,"Tensor input_1 row 3 word 0 mismatch actual %h",observed);
sba_read(32'h80001f84,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f84,observed);
if(observed!==32'h2259e242) $fatal(1,"Tensor input_1 row 3 word 1 mismatch actual %h",observed);
sba_read(32'h80001f88,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f88,observed);
if(observed!==32'h558eac07) $fatal(1,"Tensor input_1 row 3 word 2 mismatch actual %h",observed);
sba_read(32'h80001f8c,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f8c,observed);
if(observed!==32'hb3651dee) $fatal(1,"Tensor input_1 row 3 word 3 mismatch actual %h",observed);
sba_read(32'h80001f90,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f90,observed);
if(observed!==32'hc7f4fa8a) $fatal(1,"Tensor input_1 row 3 word 4 mismatch actual %h",observed);
sba_read(32'h80001f94,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f94,observed);
if(observed!==32'h2dc36404) $fatal(1,"Tensor input_1 row 3 word 5 mismatch actual %h",observed);
sba_read(32'h80001f98,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f98,observed);
if(observed!==32'h4b854b50) $fatal(1,"Tensor input_1 row 3 word 6 mismatch actual %h",observed);
sba_read(32'h80001f9c,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001f9c,observed);
if(observed!==32'he542e338) $fatal(1,"Tensor input_1 row 3 word 7 mismatch actual %h",observed);
sba_read(32'h80001fa0,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001fa0,observed);
if(observed!==32'hd8694b8d) $fatal(1,"Tensor input_1 row 3 word 8 mismatch actual %h",observed);
sba_read(32'h80001fa4,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001fa4,observed);
if(observed!==32'hb69099c7) $fatal(1,"Tensor input_1 row 3 word 9 mismatch actual %h",observed);
sba_read(32'h80001fa8,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001fa8,observed);
if(observed!==32'h0ab0b522) $fatal(1,"Tensor input_1 row 3 word 10 mismatch actual %h",observed);
sba_read(32'h80001fac,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001fac,observed);
if(observed!==32'h7403b000) $fatal(1,"Tensor input_1 row 3 word 11 mismatch actual %h",observed);
sba_read(32'h80001fb0,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001fb0,observed);
if(observed!==32'h178738a4) $fatal(1,"Tensor input_1 row 3 word 12 mismatch actual %h",observed);
sba_read(32'h80001fb4,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001fb4,observed);
if(observed!==32'h89b9c320) $fatal(1,"Tensor input_1 row 3 word 13 mismatch actual %h",observed);
sba_read(32'h80001fb8,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001fb8,observed);
if(observed!==32'hbbf9a4c0) $fatal(1,"Tensor input_1 row 3 word 14 mismatch actual %h",observed);
sba_read(32'h80001fbc,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001fbc,observed);
if(observed!==32'hd9396030) $fatal(1,"Tensor input_1 row 3 word 15 mismatch actual %h",observed);
sba_read(32'h80001e40,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e40,observed);
if(observed!==32'hcdfab323) $fatal(1,"Tensor _0 row 0 word 0 mismatch actual %h",observed);
sba_read(32'h80001e44,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e44,observed);
if(observed!==32'h1e032b3e) $fatal(1,"Tensor _0 row 0 word 1 mismatch actual %h",observed);
sba_read(32'h80001e48,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e48,observed);
if(observed!==32'hd01e636a) $fatal(1,"Tensor _0 row 0 word 2 mismatch actual %h",observed);
sba_read(32'h80001e4c,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e4c,observed);
if(observed!==32'hf39c69d2) $fatal(1,"Tensor _0 row 0 word 3 mismatch actual %h",observed);
sba_read(32'h80001e50,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e50,observed);
if(observed!==32'hbb06d25d) $fatal(1,"Tensor _0 row 0 word 4 mismatch actual %h",observed);
sba_read(32'h80001e54,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e54,observed);
if(observed!==32'hddae3608) $fatal(1,"Tensor _0 row 0 word 5 mismatch actual %h",observed);
sba_read(32'h80001e58,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e58,observed);
if(observed!==32'h032e19e9) $fatal(1,"Tensor _0 row 0 word 6 mismatch actual %h",observed);
sba_read(32'h80001e5c,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e5c,observed);
if(observed!==32'h24141fed) $fatal(1,"Tensor _0 row 0 word 7 mismatch actual %h",observed);
sba_read(32'h80001e60,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e60,observed);
if(observed!==32'hce4b3cc7) $fatal(1,"Tensor _0 row 1 word 0 mismatch actual %h",observed);
sba_read(32'h80001e64,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e64,observed);
if(observed!==32'h1109ce93) $fatal(1,"Tensor _0 row 1 word 1 mismatch actual %h",observed);
sba_read(32'h80001e68,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e68,observed);
if(observed!==32'h2253d9ee) $fatal(1,"Tensor _0 row 1 word 2 mismatch actual %h",observed);
sba_read(32'h80001e6c,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e6c,observed);
if(observed!==32'h244bf930) $fatal(1,"Tensor _0 row 1 word 3 mismatch actual %h",observed);
sba_read(32'h80001e70,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e70,observed);
if(observed!==32'hd72142a1) $fatal(1,"Tensor _0 row 1 word 4 mismatch actual %h",observed);
sba_read(32'h80001e74,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e74,observed);
if(observed!==32'hfc4aeb21) $fatal(1,"Tensor _0 row 1 word 5 mismatch actual %h",observed);
sba_read(32'h80001e78,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e78,observed);
if(observed!==32'hefbc065b) $fatal(1,"Tensor _0 row 1 word 6 mismatch actual %h",observed);
sba_read(32'h80001e7c,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e7c,observed);
if(observed!==32'hed00edc0) $fatal(1,"Tensor _0 row 1 word 7 mismatch actual %h",observed);
sba_read(32'h80001e80,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e80,observed);
if(observed!==32'h00b3f6e6) $fatal(1,"Tensor _0 row 2 word 0 mismatch actual %h",observed);
sba_read(32'h80001e84,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e84,observed);
if(observed!==32'h2fe9a933) $fatal(1,"Tensor _0 row 2 word 1 mismatch actual %h",observed);
sba_read(32'h80001e88,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e88,observed);
if(observed!==32'h2bb5a716) $fatal(1,"Tensor _0 row 2 word 2 mismatch actual %h",observed);
sba_read(32'h80001e8c,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e8c,observed);
if(observed!==32'hcf0110ad) $fatal(1,"Tensor _0 row 2 word 3 mismatch actual %h",observed);
sba_read(32'h80001e90,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e90,observed);
if(observed!==32'hf5d8093b) $fatal(1,"Tensor _0 row 2 word 4 mismatch actual %h",observed);
sba_read(32'h80001e94,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e94,observed);
if(observed!==32'ha4bcb9c5) $fatal(1,"Tensor _0 row 2 word 5 mismatch actual %h",observed);
sba_read(32'h80001e98,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e98,observed);
if(observed!==32'h203afbf8) $fatal(1,"Tensor _0 row 2 word 6 mismatch actual %h",observed);
sba_read(32'h80001e9c,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001e9c,observed);
if(observed!==32'h2d280022) $fatal(1,"Tensor _0 row 2 word 7 mismatch actual %h",observed);
sba_read(32'h80001ea0,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ea0,observed);
if(observed!==32'hf02913ef) $fatal(1,"Tensor _0 row 3 word 0 mismatch actual %h",observed);
sba_read(32'h80001ea4,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ea4,observed);
if(observed!==32'h1f350101) $fatal(1,"Tensor _0 row 3 word 1 mismatch actual %h",observed);
sba_read(32'h80001ea8,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ea8,observed);
if(observed!==32'h29c841ab) $fatal(1,"Tensor _0 row 3 word 2 mismatch actual %h",observed);
sba_read(32'h80001eac,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001eac,observed);
if(observed!==32'hd87fe3d8) $fatal(1,"Tensor _0 row 3 word 3 mismatch actual %h",observed);
sba_read(32'h80001eb0,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001eb0,observed);
if(observed!==32'h42e002d5) $fatal(1,"Tensor _0 row 3 word 4 mismatch actual %h",observed);
sba_read(32'h80001eb4,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001eb4,observed);
if(observed!==32'h085e8903) $fatal(1,"Tensor _0 row 3 word 5 mismatch actual %h",observed);
sba_read(32'h80001eb8,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001eb8,observed);
if(observed!==32'hf2cb0da3) $fatal(1,"Tensor _0 row 3 word 6 mismatch actual %h",observed);
sba_read(32'h80001ebc,observed);
$fdisplay(result_fd,"%08x %08x",32'h80001ebc,observed);
if(observed!==32'h64d3a9c3) $fatal(1,"Tensor _0 row 3 word 7 mismatch actual %h",observed);
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
