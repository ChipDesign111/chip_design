`timescale 1ns/1ps
// Upper-bound probe: keep the real SoC but override the CPU's instruction
// port with an ideal model (grant immediately, response one cycle later, data
// straight from the loaded image). It answers "how fast could the firmware run
// if instruction fetch cost nothing?", so we know whether a fetch buffer is
// worth building. Testbench-only experiment; the RTL itself is untouched.
module tb_soc;
    reg clk=0,rst_n=0;
    always #5 clk=~clk;
    wire tdo;
    my_soc_top dut(.clk_i(clk),.rst_ni(rst_n),.tck_i(1'b0),.tms_i(1'b0),.td_i(1'b0),.td_o(tdo));
    reg load_req=0,load_we=0;
    reg [3:0] load_be=15;
    reg [31:0] load_addr=0,load_data=0;
    reg [31:0] image[0:2047];
    reg [31:0] magic=0;
    integer cycles=0;
    // ideal fetch model
    reg        gnt_d=0;
    reg [31:0] addr_d=0;
    reg [31:0] boot_rom[0:1];
    always @(posedge clk) begin gnt_d<=dut.instr_req; addr_d<=dut.instr_addr; end
    wire [31:0] ideal_rdata = (addr_d[31:16]==16'h0001) ? boot_rom[addr_d[3:2]] : image[addr_d[12:2]];
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
    always @(posedge clk) if(dut.sram_req && dut.sram_we && dut.sram_addr==32'h80001fe0) magic<=dut.sram_wdata;
    integer k;
    initial begin
        // The forced instruction port deliberately violates the AXI handshake
        // seen by the fabric (the grant never reaches the xbar), so SVA
        // protocol checks must be silenced for this measurement only.
        $assertoff(0, tb_soc);
        boot_rom[0]=32'h800002b7; boot_rom[1]=32'h00028067;
        force dut.dm_master_req=load_req;force dut.dm_master_we=load_we;
        force dut.dm_master_add=load_addr;force dut.dm_master_wdata=load_data;force dut.dm_master_be=load_be;
        $readmemh("firmware.hex",image);
        #1;rst_n=0;repeat(4) @(negedge clk);#2;rst_n=1;
        repeat(7) @(posedge clk);
        repeat(20) @(negedge clk);
        sba_write(32'h0001003c,32'hb007c0de,15);
        repeat(12) @(negedge clk);
        sba_write(32'h80001ffc,image[2047],15);
        sba_write(32'h80000000,image[0],3);
        for(k=0;k<2048;k=k+1) sba_write(32'h80000000+k*4,image[k],15);
        sba_write(32'h0001003c,32'hb007c0de,15);
        @(negedge clk);
        force dut.instr_gnt    = dut.instr_req;
        force dut.instr_rvalid = gnt_d;
        force dut.instr_rdata  = ideal_rdata;
        // The real adapter still receives instr_req and would push useless
        // reads into the crossbar, flooding the shared SRAM port. Keep the
        // fabric's instruction slave port idle so this measures the
        // execution-bound floor rather than an arbitration artifact.
        force dut.slave[0].ar_valid = 1'b0;
        force dut.slave[0].aw_valid = 1'b0;
        force dut.slave[0].w_valid  = 1'b0;
        while(cycles<200000 && magic!==32'hc0dec0de) begin
            @(negedge clk);cycles=cycles+1;
            if(magic===32'hdeadbeef) $fatal(1,"CPU numerical self-check failed");
        end
        if(magic!==32'hc0dec0de) $fatal(1,"SoC timeout, PC=%h",dut.instr_addr);
        $display("IDEAL cycles=%0d time_ns=%0.3f npu_cycles=%0d",
                 cycles,$realtime,dut.i_npu_subsystem.i_npu_core.core.cycle_count);
        $finish;
    end
endmodule
