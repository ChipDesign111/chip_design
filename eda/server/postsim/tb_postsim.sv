`timescale 1ns/1ps
module tb_postsim;
  reg clk=0, rst_n=0;
  always #10 clk=~clk; // Same 20 ns system period as the physical implementation.
  wire tdo;
  my_soc_top dut(.clk_i(clk),.rst_ni(rst_n),.tck_i(1'b0),
                 .tms_i(1'b0),.td_i(1'b0),.td_o(tdo));
  reg load_req=0,load_we=0;
  reg [3:0] load_be=15;
  reg [31:0] load_addr=0,load_data=0;
  reg [31:0] image[0:2047];
  reg [31:0] magic=0;
  integer cycles=0,i;
  reg [31:0] value,stats[0:3];
  initial begin
`ifndef NO_SDF
      $sdf_annotate("timing.sdf",dut,,"sdf.log","MAXIMUM");
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
  // Observe after the annotated clock/reset paths have settled. The firmware
  // performs value-by-value hidden activation, score and class comparisons.
  always @(negedge clk) begin
    if(dut.ndmreset_n===1'b1 && dut.boot_ready===1'b0 && dut.instr_req===1'b1)
      $fatal(1,"CPU fetch before image commit");
    if(dut.sram_req===1'b1 && dut.sram_we===1'b1 && dut.sram_addr==32'h80001fe0)
      magic<=dut.sram_wdata;
  end
  initial begin
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
    while(cycles<200000 && magic!==32'hc0dec0de) begin
      @(negedge clk);#1;cycles=cycles+1;
      if(magic===32'hdeadbeef) $fatal(1,"CPU numeric self-check failed");
    end
    if(magic!==32'hc0dec0de) $fatal(1,"CPU timeout PC=%h",dut.instr_addr);
    for(i=0;i<4;i=i+1) begin
      sba_access(0,32'h80001fc0+i*4,0,15,value);stats[i]=value;
    end
    if(stats[2]===0 || stats[3]===0 || (^stats[2])===1'bx || (^stats[3])===1'bx)
      $fatal(1,"No actual DMA/MAC overlap");
    $display("FUNCTIONAL_PASS cycles=%0d npu_cycles=%0d dma_mac_overlap=%0d read_overlap=%0d write_overlap=%0d time_ns=%0.3f",
             cycles,stats[0],stats[1],stats[2],stats[3],$realtime);
    $display("ACTIVE_END time_ns=%0.3f",$realtime);
    #2;rst_n=0;repeat(4) @(negedge clk);
    if(dut.ndmreset_n!==1'b0 || dut.boot_ready!==1'b0) $fatal(1,"Reset did not revoke boot");
    $display("POSTSIM_DONE time_ns=%0.3f",$realtime);
    $finish;
  end
endmodule
