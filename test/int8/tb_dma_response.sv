`timescale 1ns/1ps
module tb_dma_response;
  reg clk=0,rst_n=0,start=0;
  reg ar_ready=0,aw_ready=0,r_valid=0,r_last=0,w_ready=0,b_valid=0;
  reg [31:0] r_data=0;
  reg [1:0] r_resp=0,b_resp=0;
  wire ar_valid,aw_valid,r_ready,w_valid,w_last,b_ready,done,error,busy;
  wire [31:0] ar_addr,aw_addr,w_data;
  wire [7:0] ar_len,aw_len;
  integer cycle=0,writes=0,reads=0,responses=0,done_edges=0,last_w_cycle=0,b_cycle=0,done_cycle=0;
  integer kind=0,checks=0,launch_cycle=0;
  reg [31:0] configured_source=32'h80001000;
  integer configured_words=16,planned_bursts=1;
  integer plan_words[0:3],plan_total[0:3];
  reg [31:0] plan_src[0:3],plan_dst[0:3];
  integer write_burst=0,write_beat=0,ar_transactions=0,aw_transactions=0;
  reg old_done=0,w_stalled=0;
  reg [31:0] held_w;
  reg held_last;
  always #5 clk=~clk;
  har_dma dut(.clk_i(clk),.rst_ni(rst_n),.reg_req_i(1'b0),.reg_we_i(1'b0),
    .reg_addr_i(5'd0),.reg_wdata_i(32'd0),.reg_rdata_o(),.npu_busy_i(1'b0),.conflict_i(1'b0),
    .auto_start_i(start),.auto_source_i(configured_source),.auto_dest_i(32'h70000100),.auto_words_i(configured_words),
    .done_o(done),.error_o(error),.busy_o(busy),.read_active_o(),.write_active_o(),
    .ar_addr_o(ar_addr),.ar_len_o(ar_len),.ar_valid_o(ar_valid),.ar_ready_i(ar_ready),
    .aw_addr_o(aw_addr),.aw_len_o(aw_len),.aw_valid_o(aw_valid),.aw_ready_i(aw_ready),
    .r_data_i(r_data),.r_resp_i(r_resp),.r_last_i(r_last),.r_valid_i(r_valid),.r_ready_o(r_ready),
    .w_data_o(w_data),.w_last_o(w_last),.w_valid_o(w_valid),.w_ready_i(w_ready),
    .b_resp_i(b_resp),.b_valid_i(b_valid),.b_ready_o(b_ready));
  function [31:0] word_at(input integer n);
    word_at=32'h51a20000+n;
  endfunction
  always @(posedge clk) begin
    cycle=cycle+1;
    if(!rst_n) begin
      writes=0;reads=0;responses=0;done_edges=0;old_done=0;w_stalled=0;
      write_burst=0;write_beat=0;ar_transactions=0;aw_transactions=0;
    end else begin
      if(w_stalled && (!w_valid || w_data!==held_w || w_last!==held_last))
        $fatal(1,"DMA_RESPONSE_FAIL W changed under backpressure");
      w_stalled=w_valid&&!w_ready;held_w=w_data;held_last=w_last;
      if(start) launch_cycle=cycle;
      if(ar_valid&&ar_ready) ar_transactions=ar_transactions+1;
      if(aw_valid&&aw_ready) aw_transactions=aw_transactions+1;
      if(r_valid&&r_ready) reads=reads+1;
      if(w_valid&&w_ready) begin
        if(writes>=configured_words || w_last!==(write_beat==plan_words[write_burst]-1)) $fatal(1,"DMA_RESPONSE_FAIL W count/last");
        if(w_data!==(kind==3 && writes>=8 ? 32'd0 : word_at(writes)))
          $fatal(1,"DMA_RESPONSE_FAIL W data index=%0d got=%h",writes,w_data);
        writes=writes+1;
        if(w_last) begin last_w_cycle=cycle;write_burst=write_burst+1;write_beat=0;end
        else write_beat=write_beat+1;
      end
      if(b_valid&&b_ready) begin
        if(responses>=planned_bursts || writes!=plan_total[responses]) $fatal(1,"DMA_RESPONSE_FAIL premature/excess B acceptance");
        responses=responses+1;b_cycle=cycle;
      end
      #1;
      if(done&&!old_done) begin
        if(responses!=planned_bursts) $fatal(1,"DMA_RESPONSE_FAIL done before/excess B handshake");
        done_edges=done_edges+1;done_cycle=cycle;
      end
      old_done=done;
    end
  end
  task automatic send_reads;
    integer i,burst,n,base_idx;
    begin
      base_idx=0;
      for(burst=0;burst<planned_bursts;burst=burst+1) begin
        repeat(2) @(negedge clk);
        ar_ready=1;
        @(posedge clk);while(!ar_valid) @(posedge clk);
        if(ar_addr!==plan_src[burst] || ar_len!=plan_words[burst]-1) $fatal(1,"DMA_RESPONSE_FAIL AR payload");
        @(negedge clk);ar_ready=0;
        n=kind==3?8:kind==4?18:plan_words[burst];
        for(i=0;i<n;i=i+1) begin
          r_data=word_at(base_idx+i);r_last=i==n-1;r_resp=(kind==1&&i==3)?2'b10:2'b00;r_valid=1;
          @(posedge clk);while(!r_ready) @(posedge clk);
          @(negedge clk);r_valid=0;
          if(i%3==0) @(negedge clk);
        end
        r_last=0;r_resp=0;base_idx=base_idx+plan_words[burst];
      end
    end
  endtask
  task automatic accept_writes(input integer delay_b);
    integer burst;
    begin
      for(burst=0;burst<planned_bursts;burst=burst+1) begin
        repeat(7) @(negedge clk);
        aw_ready=1;
        @(posedge clk);while(!aw_valid) @(posedge clk);
        if(aw_addr!==plan_dst[burst] || aw_len!=plan_words[burst]-1) $fatal(1,"DMA_RESPONSE_FAIL AW payload");
        @(negedge clk);aw_ready=0;
        while(writes<plan_total[burst]) begin
          w_ready=(cycle-launch_cycle)%5!=0;
          @(negedge clk);
        end
        w_ready=0;
        repeat(delay_b) @(negedge clk);
        b_resp=kind==2?2'b10:2'b00;b_valid=1;
        @(posedge clk);while(!b_ready) @(posedge clk);
        @(negedge clk);b_valid=0;b_resp=0;
      end
    end
  endtask
  task automatic run_case(input integer case_kind,input integer delay_b);
    integer n,remaining,take,boundary,offset;
    begin
      @(negedge clk);rst_n=0;start=0;ar_ready=0;aw_ready=0;r_valid=0;b_valid=0;w_ready=0;
      repeat(3) @(negedge clk);
      kind=case_kind;
      configured_source=kind==6?32'h80000ff0:32'h80001000;
      configured_words=kind==5?32:16;
      planned_bursts=0;remaining=configured_words;offset=0;
      while(remaining>0) begin
        take=remaining>16?16:remaining;
        boundary=1024-(((configured_source+offset*4)>>2)&1023);
        if(take>boundary) take=boundary;
        plan_words[planned_bursts]=take;plan_total[planned_bursts]=offset+take;
        plan_src[planned_bursts]=configured_source+offset*4;
        plan_dst[planned_bursts]=32'h70000100+offset*4;
        remaining=remaining-take;offset=offset+take;planned_bursts=planned_bursts+1;
      end
      rst_n=1;
      repeat(2) @(negedge clk);start=1;
      @(negedge clk);start=0;
      n=kind==3?8:kind==4?18:configured_words;
      fork
        send_reads;
        accept_writes(delay_b);
      join
      repeat(5) @(negedge clk);
      if(!done || busy || error!==((kind>=1)&&(kind<=4)) || done_edges!=1 || responses!=planned_bursts || reads!=n || ar_transactions!=planned_bursts || aw_transactions!=planned_bursts)
        $fatal(1,"DMA_RESPONSE_FAIL finish kind=%0d done=%b error=%b edges=%0d",kind,done,error,done_edges);
      if(kind==0 || kind>=5) begin
        if(dut.copied!==configured_words) $fatal(1,"DMA_RESPONSE_FAIL copied count");
      end
      $display("DMA_RESPONSE_CASE kind=%0d b_delay=%0d last_w_to_done=%0d b_to_done=%0d reads=%0d writes=%0d bursts=%0d copied=%0d elapsed=%0d",kind,delay_b,done_cycle-last_w_cycle,done_cycle-b_cycle,reads,writes,responses,dut.copied,done_cycle-launch_cycle);
      checks=checks+1;
    end
  endtask
  initial begin
    run_case(0,0);run_case(0,7);run_case(1,0);run_case(2,0);run_case(3,0);run_case(4,0);run_case(5,0);run_case(6,0);
    $display("DMA_RESPONSE_PASS checks=%0d",checks);$finish;
  end
  initial begin #100000; $fatal(1,"DMA_RESPONSE_FAIL watchdog");end
endmodule
