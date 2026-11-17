`timescale 1ns/1ps
module tb_axi_sram_reset;
  reg clk=0, raw_reset_n=0;
  // Exercise the actual SoC POR/NDM reset tree, not a copied reset model.
  integer reset_kind=0;
  wire soc_por_n=reset_kind==0 ? raw_reset_n : 1'b1;
  wire ndm_request=reset_kind==1 && !raw_reset_n;
  wire tdo;
  my_soc_top reset_source(.clk_i(clk),.rst_ni(soc_por_n),.tck_i(1'b0),
    .tms_i(1'b1),.td_i(1'b0),.td_o(tdo));
  wire txn_reset_n=reset_source.ndmreset_n;
  initial force reset_source.ndmreset=ndm_request;
  always #10 clk=~clk;
  AXI_BUS #(.AXI_ADDR_WIDTH(32),.AXI_DATA_WIDTH(32),.AXI_ID_WIDTH(4),.AXI_USER_WIDTH(1)) bus();
  wire req,we;wire [31:0] addr,wdata,rdata;wire[3:0] be;
  axi2mem #(.AXI_ID_WIDTH(4),.AXI_ADDR_WIDTH(32),.AXI_DATA_WIDTH(32),.AXI_USER_WIDTH(1),.QUIET_ON_RESET(1)) bridge(
    .clk_i(clk),.rst_ni(txn_reset_n),.slave(bus),.req_o(req),.we_o(we),.addr_o(addr),.be_o(be),.user_o(),.data_o(wdata),.user_i(1'b0),.data_i(rdata));
  my_mainmem mem(.clk_i(clk),.rst_ni(txn_reset_n),.req_i(req),.we_i(we),.be_i(be),.addr_i(addr),.wdata_i(wdata),.rdata_o(rdata));
  reg[31:0] expected[0:2047],issued_data[0:4095];
  reg[10:0] issued_addr[0:4095];reg[3:0] issued_mask[0:4095];
  integer accepted=0,writes=0,passed=0,phase,i,b,a,saved_count;
  reg[10:0] payload_addr;reg[31:0] payload_data;reg[3:0] payload_mask;
  always @(posedge clk) begin
    if(txn_reset_n===1'b0 && (req!==0 || bus.aw_ready!==0 || bus.w_ready!==0 || bus.ar_ready!==0 || bus.r_valid!==0 || bus.b_valid!==0))
      $fatal(1,"Handshake/request during qualified reset");
    if(txn_reset_n===1'b1 && req && we && |be) begin
      issued_addr[accepted]=addr[12:2];issued_data[accepted]=wdata;issued_mask[accepted]=be;accepted=accepted+1;
      for(integer j=0;j<4;j=j+1) if(be[j]) expected[addr[12:2]][j*8+:8]=wdata[j*8+:8];
    end
  end
  always @(posedge mem.sram_clk) if(mem.port_req_q===1'b1 && |mem.port_byte_we_q) begin
    if(writes>=accepted || {mem.port_addr_q,mem.port_wdata_q,mem.port_byte_we_q}!=={issued_addr[writes],issued_data[writes],issued_mask[writes]})
      $fatal(1,"Write torn, duplicated, or not accepted writes=%0d accepted=%0d",writes,accepted);
    writes=writes+1;
  end
  task idle_master;
    begin
      bus.aw_id=0;bus.aw_addr=0;bus.aw_len=0;bus.aw_size=2;bus.aw_burst=1;bus.aw_lock=0;bus.aw_cache=0;bus.aw_prot=0;bus.aw_qos=0;bus.aw_region=0;bus.aw_atop=0;bus.aw_user=0;bus.aw_valid=0;
      bus.w_data=0;bus.w_strb=0;bus.w_last=1;bus.w_user=0;bus.w_valid=0;bus.b_ready=1;
      bus.ar_id=0;bus.ar_addr=0;bus.ar_len=0;bus.ar_size=2;bus.ar_burst=1;bus.ar_lock=0;bus.ar_cache=0;bus.ar_prot=0;bus.ar_qos=0;bus.ar_region=0;bus.ar_user=0;bus.ar_valid=0;bus.r_ready=0;
    end
  endtask
  task wait_active;
    begin wait(txn_reset_n===1'b1);@(negedge clk);#2; end
  endtask
  task write_word(input integer address,input reg[31:0] data,input reg[3:0] mask);
    begin
      @(negedge clk);#2;bus.aw_addr=address*4;bus.aw_valid=1;bus.aw_len=0;bus.w_data=data;bus.w_strb=mask;bus.w_valid=1;bus.w_last=1;
      @(posedge clk);if(!bus.aw_ready || !bus.w_ready) $fatal(1,"Write not accepted");
      #1;bus.aw_valid=0;bus.w_valid=0;bus.w_data=0;
      @(posedge clk);if(!bus.b_valid) $fatal(1,"Missing write response");#1;
    end
  endtask
  task read_word(input integer address);
    begin
      @(negedge clk);#2;bus.ar_addr=address*4;bus.ar_valid=1;bus.r_ready=1;bus.ar_len=0;
      @(posedge clk);if(!bus.ar_ready) $fatal(1,"Read not accepted");#1;bus.ar_valid=0;
      @(posedge clk);if(!bus.r_valid || bus.r_data!==expected[address]) $fatal(1,"Read mismatch %0d got=%h expected=%h",address,bus.r_data,expected[address]);#1;bus.r_ready=0;
    end
  endtask
  task assert_reset_with_stale_inputs;
    reg[46:0] before_reset;
    begin
      before_reset={mem.port_addr_q,mem.port_wdata_q,mem.port_byte_we_q};
      raw_reset_n=0;idle_master();
      #0.001;if({mem.port_addr_q,mem.port_wdata_q,mem.port_byte_we_q}!==before_reset) $fatal(1,"Reset tore committed payload");
      // The shared reset has a specified clocked recognition latency. AXI
      // masters withdraw unaccepted VALIDs while their own reset is asserted.
      wait(txn_reset_n===1'b0);#1;
      if(reset_kind==1 && reset_source.por_reset_n!==1'b1)
        $fatal(1,"NDM assertion reset independent debug domain");
      bus.aw_valid=1;bus.aw_addr=0;bus.w_valid=1;bus.w_data=32'hbad0bad0;bus.w_strb=15;bus.ar_valid=1;
      repeat(3) @(negedge clk);#2;
      if(mem.port_req_q!==0) $fatal(1,"Committed request did not drain");
      idle_master();raw_reset_n=1;wait_active();
    end
  endtask
  initial begin
    idle_master();for(i=0;i<2048;i=i+1) expected[i]='x;
    repeat(5) @(negedge clk);#2;raw_reset_n=1;wait_active();
    write_word(0,32'h11223344,15);write_word(0,32'haabbccdd,5);read_word(0);
    // Read response backpressure must not shift the returned address/data.
    @(negedge clk);#2;bus.ar_valid=1;bus.ar_addr=0;bus.r_ready=0;
    @(posedge clk);#1;bus.ar_valid=0;
    repeat(3) begin @(posedge clk);if(!bus.r_valid || bus.r_data!==expected[0]) $fatal(1,"Backpressure read changed");end
    @(negedge clk);#2;bus.r_ready=1;@(posedge clk);#1;bus.r_ready=0;
    for(reset_kind=0;reset_kind<2;reset_kind=reset_kind+1) begin
    for(phase=0;phase<80;phase=phase+1) begin
      // Reset after a committed masked write, at each 0.25ns phase.
      a=64+phase;write_word(a,32'h5a5a0000+phase,15);
      @(negedge clk);#2;bus.aw_addr=a*4;bus.aw_valid=1;bus.w_valid=1;bus.w_data=32'h12340000+phase;bus.w_strb=5;bus.w_last=1;
      @(posedge clk);if(!bus.aw_ready || !bus.w_ready) $fatal(1,"Masked write handshake");
      #0.001;payload_addr=mem.port_addr_q;payload_data=mem.port_wdata_q;payload_mask=mem.port_byte_we_q;
      #(0.124+0.25*phase);assert_reset_with_stale_inputs();read_word(a);read_word(0);
      // Reset during a backpressured read, then verify preserved contents.
      @(negedge clk);#2;bus.ar_valid=1;bus.ar_addr=a*4;bus.r_ready=0;
      @(posedge clk);#0.001;#(0.124+0.25*phase);assert_reset_with_stale_inputs();read_word(a);
      // AW accepted without W: reset must not fabricate a write.
      saved_count=accepted;
      @(negedge clk);#2;bus.aw_valid=1;bus.aw_addr=0;bus.w_valid=0;
      @(posedge clk);if(!bus.aw_ready) $fatal(1,"AW-only handshake");#0.001;
      #(0.124+0.25*phase);assert_reset_with_stale_inputs();
      if(accepted!=saved_count) $fatal(1,"AW-only reset fabricated a write");read_word(0);
      // Abort an INCR burst after two accepted beats. Only those two commit.
      for(b=0;b<4;b=b+1) write_word(256+4*phase+b,32'hdead0000+b,15);
      @(negedge clk);#2;bus.aw_valid=1;bus.aw_addr=(256+4*phase)*4;bus.aw_len=3;bus.w_valid=1;bus.w_last=0;bus.w_data=phase;bus.w_strb=15;
      @(posedge clk);if(!bus.aw_ready || !bus.w_ready) $fatal(1,"Burst first handshake");#1;bus.aw_valid=0;
      @(negedge clk);#2;bus.w_data=32'habcd0000+phase;
      @(posedge clk);if(!bus.w_ready) $fatal(1,"Burst second handshake");#0.001;
      #(0.124+0.25*phase);assert_reset_with_stale_inputs();
      for(b=0;b<4;b=b+1) read_word(256+4*phase+b);
    end
    end
    repeat(3) @(negedge clk);
    if(writes!=accepted) $fatal(1,"Lost/extra write accepted=%0d actual=%0d",accepted,writes);
    passed=1;$display("AXI_SRAM_RESET_PASS phases=80 POR_scenarios=320 NDM_scenarios=320 accepted=%0d actual=%0d",accepted,writes);$finish;
  end
  initial begin #2000000;$fatal(1,"Timeout");end
endmodule
