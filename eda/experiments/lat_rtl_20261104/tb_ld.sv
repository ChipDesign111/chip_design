`timescale 1ns/1ps
// Loader latency probe: stamps every handshake of the first few SBA writes so
// the per-write cost can be attributed to a specific pipeline hop.
module tb_soc;
    reg clk=0,rst_n=0;
    always #5 clk=~clk;
    wire tdo;
    my_soc_top dut(.clk_i(clk),.rst_ni(rst_n),.tck_i(1'b0),.tms_i(1'b0),.td_i(1'b0),.td_o(tdo));
    reg load_req=0,load_we=0;
    reg [3:0] load_be=15;
    reg [31:0] load_addr=0,load_data=0;
    integer n=0;
    task sba_write(input reg [31:0] address,value,input reg [3:0] be);
        integer timeout;
        begin
            @(negedge clk);load_req=1;load_we=1;load_addr=address;load_data=value;load_be=be;timeout=0;
            if(n<4) $display("T=%0t drive",$time);
            @(posedge clk);
            while(!dut.dm_master_gnt && timeout<1000) begin @(posedge clk);timeout=timeout+1;end
            if(n<4) $display("T=%0t   gnt",$time);
            @(negedge clk);load_req=0;
            timeout=0;
            while(!dut.dm_master_r_valid && timeout<1000) begin @(posedge clk);timeout=timeout+1;end
            if(n<4) $display("T=%0t   rvalid",$time);
            @(negedge clk);
            n=n+1;
        end
    endtask
    // fabric hops, cycle-stamped
    always @(posedge clk) if(n<4) begin
        if(dut.slave[2].aw_valid) $display("T=%0t     dm aw_valid",$time);
        if(dut.master[1].aw_valid) $display("T=%0t     sram aw_valid (xbar mst)",$time);
        if(dut.i_axi2sram.req_o) $display("T=%0t     axi2sram mem req we=%b",$time,dut.i_axi2sram.we_o);
        if(dut.i_axi2sram.slave.b_valid) $display("T=%0t     axi2sram b_valid",$time);
        if(dut.slave[2].b_valid) $display("T=%0t     dm b_valid",$time);
    end
    initial begin
        force dut.dm_master_req=load_req;force dut.dm_master_we=load_we;
        force dut.dm_master_add=load_addr;force dut.dm_master_wdata=load_data;force dut.dm_master_be=load_be;
        #1;rst_n=0;repeat(4) @(negedge clk);#2;rst_n=1;
        repeat(7) @(posedge clk);
        repeat(20) @(negedge clk);
        sba_write(32'h80000000,32'h12345678,15);
        sba_write(32'h80000004,32'h12345678,15);
        sba_write(32'h80000008,32'h12345678,15);
        $finish;
    end
endmodule
