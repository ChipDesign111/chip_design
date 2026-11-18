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
  integer raw_scenario=0,raw_expected_tiles=0,raw_expected_outputs=0;
  integer raw_expected_inputs=0,raw_expected_reads=0,timeout_cycles=200000;
  integer raw_tiles=0,raw_index_writes=0,raw_data_reads=0,raw_ready_reads=0;
  integer raw_mode_entries=0,raw_mode_clears=0;
  reg [31:0] raw_w1_base=0;
  reg raw_mode_requested=0,npu_req_q=0;
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
  // Observe the CPU-visible MMIO path, not internal synthesizable state names.
  // RAW firmware must set MODE=1, start only in RAW, read every partial sum,
  // never prefetch W2, and restore MODE=0 before its final status write.
  always @(posedge clk) begin
    npu_req_q<=dut.npu_req;
    if(raw_scenario) begin
      if(dut.npu_req && !npu_req_q) begin
        if(dut.npu_we && dut.npu_addr==32'h7000003c) begin
          if(dut.npu_wdata==32'd1) begin
            raw_mode_requested<=1;raw_mode_entries<=raw_mode_entries+1;
          end else if(dut.npu_wdata==32'd0) begin
            raw_mode_requested<=0;raw_mode_clears<=raw_mode_clears+1;
          end
        end
        if(dut.npu_we && dut.npu_addr==32'h70000000 && dut.npu_wdata[0]) begin
          if(!raw_mode_requested) $fatal(1,"RAW SoC START without MODE=1");
          raw_tiles<=raw_tiles+1;
        end
        if(dut.npu_we && dut.npu_addr==32'h70000080) begin
          if(!raw_mode_requested || dut.npu_wdata[31:7]!=0)
            $fatal(1,"Invalid RAW_INDEX write data=%h",dut.npu_wdata);
          raw_index_writes<=raw_index_writes+1;
        end
        if(!dut.npu_we && dut.npu_addr==32'h70000084) raw_data_reads<=raw_data_reads+1;
        if(!dut.npu_we && dut.npu_addr==32'h70000088) raw_ready_reads<=raw_ready_reads+1;
      end
      if(dut.auto_start) begin
        if(dut.auto_source<raw_w1_base || dut.auto_source>=raw_w1_base+2048)
          $fatal(1,"RAW SoC prefetched outside the W1 workspace source=%h",dut.auto_source);
      end
    end
  end
  always @(posedge dut.auto_start) begin
    if(raw_scenario && rst_n===1'b1 && raw_mode_requested) begin
      #0.01;
      if(dut.auto_source<raw_w1_base || dut.auto_source>=raw_w1_base+2048 || dut.auto_words!==16)
        $fatal(1,"RAW SoC settling prefetch is not a 16-word W1 transfer source=%h words=%h",
               dut.auto_source,dut.auto_words);
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
    if(raw_scenario) begin
      if(!$value$plusargs("RAW_TILES=%d",raw_expected_tiles) ||
         !$value$plusargs("RAW_OUTPUTS=%d",raw_expected_outputs) ||
         !$value$plusargs("RAW_INPUTS=%d",raw_expected_inputs) ||
         !$value$plusargs("RAW_READS=%d",raw_expected_reads) ||
         !$value$plusargs("RAW_W1_BASE=%h",raw_w1_base))
        $fatal(1,"Incomplete RAW SoC scenario parameters");
      if(raw_expected_tiles<=0 || raw_expected_outputs<=0 ||
         raw_expected_inputs<=64 || raw_expected_reads<=0)
        $fatal(1,"Invalid RAW SoC scenario shape");
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
      if(raw_tiles!=raw_expected_tiles)
        $fatal(1,"RAW SoC expected %0d starts, got %0d",raw_expected_tiles,raw_tiles);
      if(raw_index_writes!=raw_expected_reads || raw_data_reads!=raw_expected_reads)
        $fatal(1,"RAW SoC expected %0d index/data reads, got %0d/%0d",
               raw_expected_reads,raw_index_writes,raw_data_reads);
      if(raw_ready_reads==0) $fatal(1,"RAW SoC firmware never polled RAW_READY");
      if(raw_mode_entries==0 || raw_mode_clears==0 || raw_mode_requested!==1'b0)
        $fatal(1,"RAW SoC MODE lifecycle incomplete entries=%0d clears=%0d requested=%0d",
               raw_mode_entries,raw_mode_clears,raw_mode_requested);
      $display("FUNCTIONAL_PASS cycles=%0d scenario=raw_soc tiles=%0d outputs=%0d inputs=%0d reads=%0d raw_ready_reads=%0d time_ns=%0.3f",
               cycles,raw_tiles,raw_expected_outputs,raw_expected_inputs,raw_data_reads,
               raw_ready_reads,$realtime);
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
