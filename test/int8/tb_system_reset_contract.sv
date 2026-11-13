`timescale 1ns/1ps
module tb_system_reset_contract;
  reg clk=0, reset_n=0;
  wire tdo;
  integer passed=0, phase, count;
  always #10 clk=~clk;
  my_soc_top dut(.clk_i(clk),.rst_ni(reset_n),.tck_i(1'b0),
    .tms_i(1'b1),.td_i(1'b0),.td_o(tdo));
  task wait_ready;
    begin
      count=0;
      while(dut.ndmreset_n!==1'b1 && count<30) begin
        @(negedge clk);#1;count=count+1;
      end
      if(dut.ndmreset_n!==1'b1) $fatal(1,"Functional reset failed to release");
      if(dut.boot_ready!==1'b0 || dut.instr_req!==1'b0)
        $fatal(1,"Reset bypassed guarded image boot");
    end
  endtask
  task check_common;
    begin
      if(dut.ndmreset_n!==1'b0 || dut.i_axi2sram.rst_ni!==1'b0 || dut.i_mainmem.rst_ni!==1'b0)
        $fatal(1,"Producer/receiver resets did not assert within two falling edges");
      if(dut.sram_req!==1'b0) $fatal(1,"SRAM request accepted during shared reset");
    end
  endtask
  initial begin
    repeat(5) @(negedge clk);#2;reset_n=1;wait_ready();
    for(phase=125;phase<20000;phase=phase+250) begin
      @(negedge clk);#(phase/1000.0);reset_n=0;
      repeat(2) @(negedge clk);#1;check_common();
      if(dut.por_reset_n!==1'b0) $fatal(1,"POR did not follow qualified external request");
      repeat(3) @(negedge clk);#2;reset_n=1;wait_ready();
      @(negedge clk);#(phase/1000.0);force dut.ndmreset=1'b1;
      repeat(2) @(negedge clk);#1;check_common();
      if(dut.por_reset_n!==1'b1) $fatal(1,"NDM reset incorrectly reset independent debug/POR domain");
      repeat(3) @(negedge clk);#2;release dut.ndmreset;wait_ready();
    end
    passed=1;
    $display("SYSTEM_RESET_CONTRACT_PASS phases=80 POR=80 NDM=80");
    $finish;
  end
endmodule
