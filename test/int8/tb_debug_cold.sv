`timescale 1ns/1ps

// Directed check for entering debug mode before the SRAM image is committed.
module tb_debug_cold;
    reg clk=0,rst_n=0;
    wire tdo;
    integer timeout;

    always #5 clk=~clk;

    my_soc_top #(.FPGA_INIT_FILE("")) dut(
        .clk_i(clk),.rst_ni(rst_n),.tck_i(1'b0),.tms_i(1'b0),
        .td_i(1'b0),.td_o(tdo)
    );

    initial begin
        #1;rst_n=0;
        repeat(12) @(negedge clk);
        rst_n=1;
        repeat(20) @(negedge clk);

        if(dut.boot_ready!==1'b0)
            $fatal(1,"boot_ready asserted without a committed image");
        if(dut.i_cpu.debug_halted_o!==1'b0)
            $fatal(1,"CPU unexpectedly halted before debug request");

        // Model OpenOCD asserting dmcontrol.haltreq while CPU waits in RESET.
        force dut.debug_req_irq=1'b1;
        timeout=0;
        while(dut.i_cpu.debug_halted_o!==1'b1 && timeout<2000) begin
            @(negedge clk);
            timeout=timeout+1;
        end

        if(dut.i_cpu.debug_halted_o!==1'b1)
            $fatal(1,"CPU failed to halt from reset, PC=%h",dut.i_cpu.core_i.pc_id);
        if(dut.boot_ready!==1'b0)
            $fatal(1,"Debug entry incorrectly asserted boot_ready");

        while(dut.i_dm_top.halted[0]!==1'b1 && timeout<2000) begin
            @(negedge clk);
            timeout=timeout+1;
        end
        if(dut.i_dm_top.halted[0]!==1'b1)
            $fatal(1,"Debug module did not observe halt, PC=%h",
                   dut.i_cpu.core_i.pc_id);

        $display("DEBUG_COLD PASS halt_cycles=%0d boot_ready=%0d pc=%h dm_halted=%0d",
                 timeout,dut.boot_ready,dut.i_cpu.core_i.pc_id,dut.i_dm_top.halted[0]);
        release dut.debug_req_irq;
        #1;
        $finish;
    end
endmodule
