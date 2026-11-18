`timescale 1ns/1ps
module tb_postsim;
  reg clk=0, rst_n=0;
  // Keep the board clock low while initial native-model states settle.
  // Reset remains asserted. The first rising edge is at 50 ns; every later
  // rising edge is 20 ns apart, matching physical STA and SDF. No checks are
  // disabled during this startup interval or any SDF run.
  initial begin #40; forever #10 clk=~clk; end
  // The board starts with its drivers disconnected while native IO tie and
  // pull controls settle. This changes stimulus, never the IO model/checks.
  reg pad_drive_en=0;
  integer pad_drive_ps=2000;
  wire [4:0] board_pads;
  assign board_pads=pad_drive_en ? {clk,rst_n,3'b000} : 5'bzzzzz;
  initial begin
    if(!$value$plusargs("PAD_DRIVE_PS=%d",pad_drive_ps)) pad_drive_ps=2000;
    if(pad_drive_ps<0 || pad_drive_ps>5000) $fatal(1,"Board drive must settle before first clock");
    #(pad_drive_ps/1000.0);pad_drive_en=1;
    $display("PAD_DRIVE_ON time_ns=%0.3f delay_ps=%0d",$realtime,pad_drive_ps);
  end
  wire tdo;
  my_soc_top dut(.clk_i(board_pads[4]),.rst_ni(board_pads[3]),.tck_i(board_pads[2]),
                 .tms_i(board_pads[1]),.td_i(board_pads[0]),.td_o(tdo));
  reg load_req=0,load_we=0;
  reg [3:0] load_be=15;
  reg [31:0] load_addr=0,load_data=0;
  reg [31:0] image[0:2047];
  reg [31:0] magic=0;
  integer cycles=0,i;
  integer reset_offset_ps=2000;
  integer raw_scenario=0,raw_range_file=0,soc_cpu_only=0,soc_har_benchmark=0;
  integer raw_expected_tiles=0,raw_expected_outputs=0;
  integer raw_expected_inputs=0,raw_expected_reads=0,timeout_cycles=200000;
  integer raw_prefetches=0;
  integer raw_dma_range_count=0,i_range;
  integer raw_mode_entries=0,raw_mode_clears=0;
  reg [31:0] raw_w1_base=0;
  reg [31:0] raw_dma_ranges[0:64];
  reg raw_mode_previous=0;
  bit raw_source_valid;
  reg [31:0] value,stats[0:3];
  initial begin
`ifndef NO_SDF
`ifdef SDF_MINIMUM
      $sdf_annotate("timing.sdf",dut,,"sdf.log","MINIMUM");
`else
      $sdf_annotate("timing.sdf",dut,,"sdf.log","MAXIMUM");
`endif
      $display("ANNOTATION_CALLED path=timing.sdf time_ns=%0.3f",$realtime);
`else
      $display("NO_SDF_CONTROL");
`endif
  end
  integer edge_count=0;
  always @(posedge dut.i_pad_clk.C) begin
    if(edge_count<4) $display("CLOCK_AT_CORE time_ns=%0.3f",$realtime);
    edge_count=edge_count+1;
  end
  // The post-PNR mapper may fold the one-cycle MMIO req pulse. Observe the
  // surviving RAW mode state and every autonomous DMA prefetch instead. CPU
  // firmware self-checks all 66 RAW index/data reads and exact arithmetic.
  always @(posedge clk) begin
    if(raw_scenario) begin
      raw_mode_previous<=dut.i_npu_subsystem.i_npu_core.raw_mode;
      if(dut.i_npu_subsystem.i_npu_core.raw_mode && !raw_mode_previous)
        raw_mode_entries<=raw_mode_entries+1;
      if(!dut.i_npu_subsystem.i_npu_core.raw_mode && raw_mode_previous)
        raw_mode_clears<=raw_mode_clears+1;
      if(dut.auto_start) begin
        raw_source_valid=0;
        if(raw_range_file) begin
          for(i_range=0;i_range<raw_dma_range_count;i_range=i_range+1)
            if(dut.auto_source>=raw_dma_ranges[1+2*i_range] &&
               dut.auto_source+64<=raw_dma_ranges[2+2*i_range] &&
               (dut.auto_source-raw_dma_ranges[1+2*i_range])%64==0)
              raw_source_valid=1;
        end else if(dut.auto_source>=raw_w1_base &&
                    dut.auto_source<raw_w1_base+2048) begin
          raw_source_valid=1;
        end
        if(!raw_source_valid)
          $fatal(1,"RAW SoC prefetched outside an approved W1 source=%h",dut.auto_source);
        if(dut.auto_words!=16)
          $fatal(1,"RAW SoC issued a non-W1 descriptor");
        raw_prefetches<=raw_prefetches+1;
      end
    end
  end
  task sba_access(input bit writing,input reg [31:0] address,data,
                  input reg [3:0] be,output reg [31:0] response);
    integer count;
    begin
      @(negedge clk); load_req=1;load_we=writing;load_addr=address;
      load_data=data;load_be=be;count=0;
      @(posedge clk);
      while(dut.dm_master_gnt!==1'b1 && count<1000) begin
        @(posedge clk);count=count+1;
      end
      if(count==1000) $fatal(1,"SBA grant timeout");
      @(negedge clk);load_req=0;count=0;
      while(dut.dm_master_r_valid!==1'b1 && count<1000) begin
        @(posedge clk);#4;count=count+1;
      end
      if(count==1000) $fatal(1,"SBA response timeout");
      response=dut.dm_master_r_rdata;
      @(negedge clk);
    end
  endtask
  task write_word(input reg [31:0] address,data,input reg [3:0] be);
    reg [31:0] ignored;
    sba_access(1,address,data,be,ignored);
  endtask
  // Observe after the annotated clock/reset paths have settled. The firmware
  // performs value-by-value hidden activation, score and class comparisons.
  always @(negedge clk) begin
    if(dut.ndmreset_n===1'b1 && dut.boot_ready===1'b0 && dut.instr_req===1'b1)
      $fatal(1,"CPU fetch before image commit");
  end
  // Observe the physical write at the macro clock, independent of the AXI
  // command/response phase. Do not report completion before the SRAM access.
  always @(posedge dut.i_mainmem.i_sram.i_macro.CLK) begin
    if(dut.i_mainmem.i_sram.i_macro.CEN===1'b0 &&
       dut.i_mainmem.i_sram.i_macro.WEN===4'b0000 &&
       dut.i_mainmem.i_sram.i_macro.A===11'h7f8)
      magic<=dut.i_mainmem.i_sram.i_macro.D;
  end
  initial begin
    raw_scenario=$test$plusargs("RAW_SCENARIO");
    raw_range_file=$test$plusargs("RAW_RANGE_FILE");
    soc_cpu_only=$test$plusargs("SOC_SCENARIO_CPU_ONLY");
    soc_har_benchmark=$test$plusargs("SOC_SCENARIO_HAR_BENCHMARK");
    if(soc_cpu_only && soc_har_benchmark) $fatal(1,"Conflicting SoC-only scenario flags");
    if(raw_scenario && (soc_cpu_only || soc_har_benchmark))
      $fatal(1,"RAW and SoC-only scenario flags cannot be combined");
    if(raw_scenario) begin
      if(!$value$plusargs("RAW_TILES=%d",raw_expected_tiles) ||
         !$value$plusargs("RAW_OUTPUTS=%d",raw_expected_outputs) ||
         !$value$plusargs("RAW_INPUTS=%d",raw_expected_inputs) ||
         !$value$plusargs("RAW_READS=%d",raw_expected_reads) ||
         !$value$plusargs("RAW_W1_BASE=%h",raw_w1_base))
        $fatal(1,"Incomplete RAW SoC scenario parameters");
      if(raw_expected_tiles<=0 || raw_expected_outputs<=0 ||
         raw_expected_inputs<=0 || raw_expected_reads<=0)
        $fatal(1,"Invalid RAW SoC scenario shape");
      if(raw_range_file) begin
        $readmemh("dma_ranges.hex",raw_dma_ranges);
        raw_dma_range_count=raw_dma_ranges[0];
        if(raw_dma_range_count<=0 || raw_dma_range_count>32)
          $fatal(1,"Invalid RAW direct-DMA range count");
      end
      timeout_cycles=100000+raw_expected_tiles*50000;
    end
    force dut.dm_master_req=load_req;force dut.dm_master_we=load_we;
    force dut.dm_master_add=load_addr;force dut.dm_master_wdata=load_data;
    force dut.dm_master_be=load_be;
    $readmemh("firmware.hex",image);
    #1;rst_n=0;repeat(4) @(negedge clk);#2;rst_n=1;
    repeat(7) @(posedge clk);#1;
    if(dut.ndmreset_n!==1'b0) $fatal(1,"Reset released before8edges");
    repeat(20) @(negedge clk);
    $display("ACTIVE_START time_ns=%0.3f",$realtime);
    write_word(32'h0001003c,32'hb007c0de,15);
    repeat(12) @(negedge clk);
    if(dut.boot_ready!==1'b0 || dut.instr_req!==1'b0) $fatal(1,"Key alone started CPU");
    write_word(32'h80001ffc,image[2047],15);
    write_word(32'h80000000,image[0],3);
    if(dut.i_bootram.loaded_words!==0) $fatal(1,"Incomplete image counted");
    for(i=0;i<2048;i=i+1) begin
      write_word(32'h80000000+i*4,image[i],15);
      if(i==31) begin
        write_word(32'h0001003c,32'hb007c0de,15);
        if(dut.boot_ready!==1'b0) $fatal(1,"Partial image started CPU");
      end
    end
    if(dut.boot_ready!==1'b0) $fatal(1,"Image needs explicit commit");
    write_word(32'h0001003c,32'hdeadbeef,15);repeat(8) @(negedge clk);
    if(dut.boot_ready!==1'b0) $fatal(1,"Wrong commit key started CPU");
    write_word(32'h0001003c,32'hb007c0de,15);
    $display("CPU_WAIT_START time_ns=%0.3f",$realtime);
    while(cycles<timeout_cycles && magic!==32'hc0dec0de) begin
      @(negedge clk);#1;cycles=cycles+1;
      if(magic===32'hdeadbeef) $fatal(1,"CPU numeric self-check failed");
    end
    if(magic!==32'hc0dec0de) $fatal(1,"CPU timeout PC=%h",dut.instr_addr);
    if(raw_scenario) begin
      if(raw_prefetches!=raw_expected_tiles*32)
        $fatal(1,"RAW SoC expected %0d W1 prefetches, got %0d",
               raw_expected_tiles*32,raw_prefetches);
      if(raw_mode_entries!=1 || raw_mode_clears!=1 ||
         dut.i_npu_subsystem.i_npu_core.raw_mode!==1'b0)
        $fatal(1,"RAW SoC MODE lifecycle incomplete entries=%0d clears=%0d final=%0d",
               raw_mode_entries,raw_mode_clears,dut.i_npu_subsystem.i_npu_core.raw_mode);
      $display("FUNCTIONAL_PASS cycles=%0d scenario=raw_soc tiles=%0d outputs=%0d inputs=%0d reads=%0d raw_prefetches=%0d mode_entries=%0d mode_clears=%0d time_ns=%0.3f",
               cycles,raw_expected_tiles,raw_expected_outputs,raw_expected_inputs,
               raw_expected_reads,raw_prefetches,raw_mode_entries,raw_mode_clears,$realtime);
    end else if(soc_cpu_only) begin
      $display("FUNCTIONAL_PASS cycles=%0d scenario=cpu_only time_ns=%0.3f",
               cycles,$realtime);
    end else if(soc_har_benchmark) begin
      $display("FUNCTIONAL_PASS cycles=%0d scenario=har_benchmark time_ns=%0.3f",
               cycles,$realtime);
    end else begin
      for(i=0;i<4;i=i+1) begin
        sba_access(0,32'h80001fc0+i*4,0,15,value);stats[i]=value;
      end
      if(stats[2]===0 || stats[3]===0 || (^stats[2])===1'bx || (^stats[3])===1'bx)
        $fatal(1,"No actual DMA/MAC overlap");
      $display("FUNCTIONAL_PASS cycles=%0d npu_cycles=%0d dma_mac_overlap=%0d read_overlap=%0d write_overlap=%0d time_ns=%0.3f",
               cycles,stats[0],stats[1],stats[2],stats[3],$realtime);
    end
    $display("ACTIVE_END time_ns=%0.3f",$realtime);
    if(!$value$plusargs("RESET_OFFSET_PS=%d",reset_offset_ps)) reset_offset_ps=2000;
    if(reset_offset_ps<1 || reset_offset_ps>=20000) $fatal(1,"Reset phase must be inside one20ns period");
    #(reset_offset_ps/1000.0);
    $display("RESET_ASSERT offset_ps=%0d time_ns=%0.3f",reset_offset_ps,$realtime);
    rst_n=0;repeat(4) @(negedge clk);
    if(dut.ndmreset_n!==1'b0 || dut.boot_ready!==1'b0) $fatal(1,"Reset did not revoke boot");
    if(dut.i_mainmem.i_sram.i_macro.CEN!==1'b1) $fatal(1,"SRAM requests continued during reset");
    $display("POSTSIM_DONE time_ns=%0.3f",$realtime);
    $finish;
  end
endmodule
