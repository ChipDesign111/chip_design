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
  integer cycles=0,i,check_words=0;
  reg [95:0] expected_checks[0:1023];
  integer reset_offset_ps=2000;
  reg [31:0] value,stats[0:3];
  reg dmi_valid=0,dmi_response_ready=0;
  reg [6:0] dmi_address=0;
  reg [31:0] dmi_data=0;
  reg [1:0] dmi_operation=0;
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
  // Drive the system-clock DMI boundary, downstream of JTAG CDC. The real
  // DMCONTROL flop generates NDM synchronously; never force its output.
  // Gate netlists flatten the request/response structure into these nets.
  task dmi_access(input bit writing,input reg [6:0] address,
                  input reg [31:0] data,output reg [31:0] response);
    integer count;
    begin
      @(negedge clk);#2;
      if(dut.debug_req_ready!==1'b1) $fatal(1,"DMI not ready before write");
      dmi_address=address;dmi_data=data;dmi_operation=writing ? 2'b10 : 2'b01;dmi_valid=1;
      @(posedge clk);#5;
      if(dut.debug_req_ready!==1'b1) $fatal(1,"DMI write not accepted");
      @(negedge clk);#2;dmi_valid=0;count=0;
      while(dut.debug_resp_valid!==1'b1 && count<100) begin
        @(negedge clk);#2;count=count+1;
      end
      if(count==100) $fatal(1,"DMI response timeout");
      response=dut.\debug_resp[data] ;
      dmi_response_ready=1;
      @(negedge clk);#2;dmi_response_ready=0;
    end
  endtask
  task dmcontrol_write(input reg [31:0] data);
    reg [31:0] ignored,observed;
    begin
      dmi_access(1,7'h10,data,ignored);
      dmi_access(0,7'h10,0,observed);
      // The constant-success response-status alias is not driven in the
      // optimized physical export. Check actual registered DMCONTROL data
      // through the response FIFO instead; bits1:0 are ndmreset/dmactive.
      if((observed & 32'h3)!==(data & 32'h3))
        $fatal(1,"DMCONTROL readback failed expected=%h actual=%h",data,observed);
      $display("DMCONTROL_READBACK_PASS value=%h time_ns=%0.3f",observed & 32'h3,$realtime);
    end
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
    force dut.dm_master_req=load_req;force dut.dm_master_we=load_we;
    force dut.dm_master_add=load_addr;force dut.dm_master_wdata=load_data;
    force dut.dm_master_be=load_be;
    $readmemh("firmware.hex",image);
    if($value$plusargs("CHECK_WORDS=%d",check_words)) begin
      if(check_words<1 || check_words>1024) $fatal(1,"Invalid expected check count");
      $readmemh("expected_checks.hex",expected_checks,0,check_words-1);
    end
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
    while(cycles<200000 && magic!==32'hc0dec0de) begin
      @(negedge clk);#1;cycles=cycles+1;
      if(magic===32'hdeadbeef) $fatal(1,"CPU numeric self-check failed");
    end
    if(magic!==32'hc0dec0de) $fatal(1,"CPU timeout PC=%h",dut.instr_addr);
    if(check_words>0) begin
      for(i=0;i<check_words;i=i+1) begin
        sba_access(0,expected_checks[i][95:64],0,15,value);
        if((value & expected_checks[i][31:0]) !== (expected_checks[i][63:32] & expected_checks[i][31:0]))
          $fatal(1,"Model check %0d addr=%h expected=%h actual=%h",i,expected_checks[i][95:64],expected_checks[i][63:32],value);
      end
      $display("MODEL_CHECKS_PASS words=%0d",check_words);
      sba_access(0,32'h7000000c,0,15,stats[0]);
      sba_access(0,32'h7000001c,0,15,stats[1]);
      sba_access(0,32'h70000034,0,15,stats[2]);
      sba_access(0,32'h70000038,0,15,stats[3]);
    end else for(i=0;i<4;i=i+1) begin
      sba_access(0,32'h80001fc0+i*4,0,15,value);stats[i]=value;
    end
    if(check_words==0 && (stats[2]===0 || stats[3]===0 || (^stats[2])===1'bx || (^stats[3])===1'bx))
      $fatal(1,"No actual DMA/MAC overlap");
    $display("FUNCTIONAL_PASS cycles=%0d npu_cycles=%0d dma_mac_overlap=%0d read_overlap=%0d write_overlap=%0d time_ns=%0.3f",
             cycles,stats[0],stats[1],stats[2],stats[3],$realtime);
    $display("ACTIVE_END time_ns=%0.3f",$realtime);
    if(!$value$plusargs("RESET_OFFSET_PS=%d",reset_offset_ps)) reset_offset_ps=2000;
    if(reset_offset_ps<1 || reset_offset_ps>=20000) $fatal(1,"Reset phase must be inside one20ns period");
    // Exercise actual DMCONTROL writes as well as the external POR input.
    // NDM is generated by a real posedge DM register, not an asynchronous
    // forced transition on its output near the falling-edge sampler.
    #(reset_offset_ps/1000.0);
    @(negedge clk);#2;
    force dut.debug_req_valid=dmi_valid;
    force dut.\debug_req[addr] =dmi_address;
    force dut.\debug_req[op] =dmi_operation;
    force dut.\debug_req[data] =dmi_data;
    force dut.debug_resp_ready=dmi_response_ready;
    dmcontrol_write(32'h00000001); // dmactive
    dmcontrol_write(32'h00000003); // dmactive + ndmreset
    if(dut.ndmreset!==1'b1) $fatal(1,"DMCONTROL did not assert NDM");
    $display("NDM_RESET_ASSERT offset_ps=%0d time_ns=%0.3f",reset_offset_ps,$realtime);
    repeat(4) @(negedge clk);
    if(dut.ndmreset_n!==1'b0 || dut.boot_ready!==1'b0) $fatal(1,"NDM reset did not revoke boot");
    if(dut.por_reset_n!==1'b1) $fatal(1,"NDM reset disturbed independent debug domain");
    if(dut.i_mainmem.i_sram.i_macro.CEN!==1'b1) $fatal(1,"SRAM requests continued during NDM reset");
    dmcontrol_write(32'h00000001);
    if(dut.ndmreset!==1'b0) $fatal(1,"DMCONTROL did not release NDM");
    repeat(16) @(negedge clk);#2;
    if(dut.ndmreset_n!==1'b1 || dut.boot_ready!==1'b0 || dut.instr_req!==1'b0)
      $fatal(1,"NDM release bypassed guarded boot");
    if(dut.i_mainmem.i_sram.i_macro.CEN!==1'b1) $fatal(1,"NDM release issued stale SRAM access");
    $display("NDM_RESET_PASS time_ns=%0.3f",$realtime);
    $display("DMCONTROL_RESET_PASS writes=3 readbacks=3 time_ns=%0.3f",$realtime);
    @(negedge clk);
    #(reset_offset_ps/1000.0);
    $display("RESET_ASSERT offset_ps=%0d time_ns=%0.3f",reset_offset_ps,$realtime);
    rst_n=0;repeat(4) @(negedge clk);
    if(dut.ndmreset_n!==1'b0 || dut.boot_ready!==1'b0) $fatal(1,"Reset did not revoke boot");
    if(dut.i_mainmem.i_sram.i_macro.CEN!==1'b1) $fatal(1,"SRAM requests continued during reset");
    $display("POSTSIM_DONE time_ns=%0.3f",$realtime);
    $finish;
  end
endmodule
