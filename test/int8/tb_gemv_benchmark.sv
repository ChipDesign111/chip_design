`timescale 1ns/1ps
// Same complete SoC and Debug SBA loader for both backends. Timing uses
// accepted SRAM BEGIN/END stores; checking runs strictly after END.
module tb_gemv_benchmark;
    reg clk=0,rst_n=0;
    always #5 clk=~clk;
    wire tdo;
    my_soc_top dut(.clk_i(clk),.rst_ni(rst_n),.tck_i(1'b0),.tms_i(1'b0),.td_i(1'b0),.td_o(tdo));
    reg load_req=0,load_we=0;
    reg [3:0] load_be=15;
    reg [31:0] load_addr=0,load_data=0;
    reg [31:0] image[0:2047],expected[0:2047];
    reg [31:0] layout[0:128],phase_pc[0:6];
    reg [31:0] dma_ranges[0:64];
    reg [8191:0] written=0;
    reg [31:0] magic=0;
    integer tick=0,begin_tick=-1,end_tick=-1,phase=0;
    integer phase_cycles[0:6];
    integer expected_tiles,tiles=0,completed_tiles=0,tile_tick=-1;
    integer expected_batch=1;
    integer npu_cycles=0,fc1_cycles=0,read_overlap=0,write_overlap=0,total_overlap=0;
    integer dma_descriptors=0;
    integer i,j,lane,byte_address,word_address,cycles=0;
    bit active=0,ended=0,done_before,valid_dma_source;

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
        tick=tick+1;
        if(dut.ndmreset_n && !dut.boot_ready && dut.instr_req)
            $fatal(1,"CPU fetched before image commit");
        if(dut.boot_ready && dut.sram_req && dut.sram_we && dut.sram_be==15) begin
            if(dut.sram_addr==32'h80001fe0) magic<=dut.sram_wdata;
            if(dut.sram_addr==32'h80001fc0) begin
                if(dut.sram_wdata==1) begin
                    if(active || ended) $fatal(1,"Duplicate benchmark BEGIN");
                    active=1;begin_tick=tick;
                end else if(dut.sram_wdata==2) begin
                    if(!active || ended) $fatal(1,"Invalid benchmark END");
                    for(i=0;i<layout[0];i=i+1)
                        for(j=layout[1+4*i];j<layout[2+4*i];j=j+1)
                            if(!written[j-32'h80000000]) $fatal(1,"Missing output before END: %h",j);
                    active=0;ended=1;end_tick=tick;
                end else $fatal(1,"Invalid benchmark marker");
            end
        end
        if(active) begin
            // Legal ID issue PCs only, never speculative instruction fetches.
            // These passive phase windows add no instructions to either path.
            if(dut.i_cpu.core_i.id_valid && dut.i_cpu.core_i.is_decoding)
                for(i=0;i<7;i=i+1)
                    if(phase_pc[i]!=0 && dut.i_cpu.core_i.pc_id==phase_pc[i]) phase=i;
            phase_cycles[phase]=phase_cycles[phase]+1;
        end
        if(dut.boot_ready && dut.sram_req) begin
            word_address=dut.sram_addr & 32'hfffffffc;
            for(i=0;i<layout[0];i=i+1) begin
                if(!dut.sram_we && active && word_address<layout[4+4*i] &&
                   word_address+4>layout[3+4*i]) $fatal(1,"Golden read before END");
                for(lane=0;lane<4;lane=lane+1) begin
                    byte_address=word_address+lane;
                    if(dut.sram_we && dut.sram_be[lane] &&
                       byte_address>=layout[1+4*i] && byte_address<layout[2+4*i]) begin
                        if(!active) $fatal(1,"Output outside measured interval");
                        if(dut.sram_wdata[lane*8+:8] !== expected[(word_address>>2)&2047][lane*8+:8])
                            $fatal(1,"Incorrect computed output byte at %h",byte_address);
                        written[byte_address-32'h80000000]=1;
                    end
                end
            end
        end
        if(dut.boot_ready && expected_tiles==0 && (dut.npu_req || dut.auto_start || dut.npu_busy))
            $fatal(1,"CPU-only backend accessed NPU or DMA");
        if(dut.i_npu_subsystem.i_npu_core.start) begin
            if(!active || !dut.i_npu_subsystem.i_npu_core.raw_mode || tile_tick>=0)
                $fatal(1,"Invalid RAW start");
            if(dut.i_npu_subsystem.i_npu_core.batch_count!=expected_batch)
                $fatal(1,"Incorrect RAW hardware batch");
            tiles=tiles+1;tile_tick=tick;
        end
        if(dut.npu_busy && dut.i_npu_subsystem.i_npu_core.layer)
            $fatal(1,"RAW executed FC2");
        if(dut.auto_start) begin
            valid_dma_source=0;
            for(i=0;i<dma_ranges[0];i=i+1)
                if(dut.auto_source>=dma_ranges[1+2*i] &&
                   dut.auto_source+64<=dma_ranges[2+2*i] &&
                   (dut.auto_source-dma_ranges[1+2*i])%64==0) valid_dma_source=1;
            if(!active || !valid_dma_source || dut.auto_words!=16)
                $fatal(1,"Invalid W1 descriptor or W2 prefetch");
            dma_descriptors=dma_descriptors+1;
        end
        done_before=dut.i_npu_subsystem.i_npu_core.done;
        #1;
        if(!done_before && dut.i_npu_subsystem.i_npu_core.done) begin
            if(tile_tick<0 || tick-tile_tick!=dut.i_npu_subsystem.i_npu_core.core.cycle_count ||
               dut.i_npu_subsystem.i_npu_core.core.fc1_cycles!=128*expected_batch ||
               dut.i_npu_subsystem.i_npu_core.core.fc2_cycles!=0)
                $fatal(1,"NPU interval/counters disagree");
            completed_tiles=completed_tiles+1;tile_tick=-1;
            npu_cycles=npu_cycles+dut.i_npu_subsystem.i_npu_core.core.cycle_count;
            fc1_cycles=fc1_cycles+dut.i_npu_subsystem.i_npu_core.core.fc1_cycles;
            read_overlap=read_overlap+dut.i_npu_subsystem.i_npu_core.core.read_overlap_count;
            write_overlap=write_overlap+dut.i_npu_subsystem.i_npu_core.core.write_overlap_count;
            total_overlap=total_overlap+dut.i_npu_subsystem.i_npu_core.core.overlap_count;
        end
    end

    initial begin
        if(!$value$plusargs("TILES=%d",expected_tiles)) $fatal(1,"TILES required");
        if(!$value$plusargs("BATCH=%d",expected_batch)) expected_batch=1;
        if(expected_batch<1 || expected_batch>4) $fatal(1,"Invalid RAW batch");
        for(i=0;i<7;i=i+1) phase_cycles[i]=0;
        $readmemh("bench_layout.hex",layout);
        $readmemh("phase_pcs.hex",phase_pc);
        $readmemh("dma_ranges.hex",dma_ranges);
        $readmemh("expected.hex",expected);
        if(layout[0]<1 || layout[0]>32) $fatal(1,"Invalid layer count");
        if(dma_ranges[0]>32) $fatal(1,"Invalid DMA range count");
        force dut.dm_master_req=load_req;force dut.dm_master_we=load_we;
        force dut.dm_master_add=load_addr;force dut.dm_master_wdata=load_data;force dut.dm_master_be=load_be;
        $readmemh("firmware.hex",image);
        #1;rst_n=0;repeat(4) @(negedge clk);#2;rst_n=1;
        repeat(30) @(negedge clk);
        for(j=0;j<2048;j=j+1) sba_write(32'h80000000+j*4,image[j]);
        sba_write(32'h0001003c,32'hb007c0de);
        while(cycles<2000000 && magic!==32'hc0dec0de) begin
            @(negedge clk);cycles=cycles+1;
            if(magic===32'hdeadbeef) $fatal(1,"CPU self-check failed PC=%h",dut.instr_addr);
        end
        if(magic!==32'hc0dec0de || !ended || begin_tick<0 || end_tick<=begin_tick)
            $fatal(1,"Benchmark timeout or missing markers PC=%h",dut.instr_addr);
        if(tiles!=expected_tiles || completed_tiles!=expected_tiles || tile_tick>=0 || dma_descriptors!=32*expected_tiles)
            $fatal(1,"Incorrect RAW task count: %0d/%0d expected %0d",tiles,completed_tiles,expected_tiles);
        if(dut.i_npu_subsystem.i_npu_core.raw_mode) $fatal(1,"Legacy mode was not restored");
        j=0;for(i=0;i<7;i=i+1) j=j+phase_cycles[i];
        if(j!=end_tick-begin_tick) $fatal(1,"Phase intervals do not sum to elapsed cycles");
        $display("GEMV_BENCH_PASS cycles=%0d setup_cycles=%0d input_pack_cycles=%0d weight_pack_cycles=%0d npu_wait_cycles=%0d read_reduce_cycles=%0d postprocess_cycles=%0d cpu_mac_cycles=%0d tiles=%0d npu_cycles=%0d fc1_issue_cycles=%0d DMA_read_MAC_overlap=%0d DMA_write_MAC_overlap=%0d DMA_MAC_total_overlap=%0d dma_descriptors=%0d",
                 end_tick-begin_tick,phase_cycles[0],phase_cycles[1],phase_cycles[2],phase_cycles[3],phase_cycles[4],phase_cycles[5],phase_cycles[6],
                 tiles,npu_cycles,fc1_cycles,read_overlap,write_overlap,total_overlap,dma_descriptors);
        $finish;
    end
endmodule
