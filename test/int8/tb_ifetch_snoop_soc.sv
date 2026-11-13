`timescale 1ns/1ps
// Exercise the real SRAM write/alias boundary through Debug SBA. The CPU's
// instruction request is driven explicitly; this is not a firmware/JTAG test.
module tb_ifetch_snoop_soc;
    reg clk=0,rst_n=0;
    wire tdo;
    always #5 clk=~clk;
    my_soc_top dut(.clk_i(clk),.rst_ni(rst_n),.tck_i(1'b0),.tms_i(1'b0),.td_i(1'b0),.td_o(tdo));
    reg load_req=0,load_we=0,fetch_req=0;
    reg [3:0] load_be=15;
    reg [31:0] load_addr=0,load_data=0,fetch_addr=0;
    integer checks=0,accepted_writes=0,alias_writes=0,zero_strobes=0;

    task sba_write(input reg [31:0] address,value,input reg [3:0] be);
        integer timeout;
        begin
            @(negedge clk);load_req=1;load_we=1;load_addr=address;load_data=value;load_be=be;timeout=0;
            @(posedge clk);
            while(!dut.dm_master_gnt && timeout<1000) begin @(posedge clk);timeout=timeout+1;end
            if(timeout>=1000) $fatal(1,"SNOOP_SOC_FAIL SBA grant timeout");
            @(negedge clk);load_req=0;timeout=0;
            while(!dut.dm_master_r_valid && timeout<1000) begin @(posedge clk);timeout=timeout+1;end
            if(timeout>=1000) $fatal(1,"SNOOP_SOC_FAIL SBA response timeout");
            @(negedge clk);
        end
    endtask

    task fetch(input reg [31:0] address,value,input integer latency_kind=0);
        integer timeout;
        reg accepted;
        begin
            @(negedge clk);fetch_req=1;fetch_addr=address;timeout=0;accepted=0;
            while(!accepted && timeout<1000) begin
                @(posedge clk);accepted=dut.instr_gnt;
                if($isunknown(accepted)) $fatal(1,"SNOOP_SOC_FAIL unknown grant");
                if(timeout==0 && latency_kind==1 && !accepted)
                    $fatal(1,"SNOOP_SOC_FAIL unaffected line lost addr=%h",address);
                if(timeout==0 && latency_kind==2 && accepted)
                    $fatal(1,"SNOOP_SOC_FAIL global invalidate did not miss");
                #2;
                if(accepted && (dut.instr_rvalid!==1'b1 || dut.instr_rdata!==value))
                    $fatal(1,"SNOOP_SOC_FAIL data addr=%h got=%h expected=%h",address,dut.instr_rdata,value);
                timeout=timeout+1;
            end
            if(!accepted) $fatal(1,"SNOOP_SOC_FAIL fetch timeout addr=%h",address);
            @(negedge clk);fetch_req=0;
            repeat(2) @(negedge clk);
            if(dut.instr_rvalid) $fatal(1,"SNOOP_SOC_FAIL duplicate response");
            checks=checks+1;
        end
    endtask

    always @(posedge clk) begin
        if(dut.ndmreset_n && dut.sram_req && dut.sram_we) begin
            accepted_writes=accepted_writes+1;
            if(dut.sram_be==0) begin
                zero_strobes=zero_strobes+1;
                if(dut.i_ifetch.snoop_valid_i)
                    $fatal(1,"SNOOP_SOC_FAIL zero byte enables invalidated cache");
            end else begin
                if(!dut.i_ifetch.snoop_valid_i)
                    $fatal(1,"SNOOP_SOC_FAIL SRAM write not observed");
                if(dut.i_ifetch.snoop_addr_i!==(32'h80000000 | (dut.sram_addr & 32'h1fff)))
                    $fatal(1,"SNOOP_SOC_FAIL physical alias normalization");
                if(dut.sram_addr>=32'h80002000) alias_writes=alias_writes+1;
            end
        end
    end

    initial begin
        force dut.dm_master_req=load_req;force dut.dm_master_we=load_we;
        force dut.dm_master_add=load_addr;force dut.dm_master_wdata=load_data;force dut.dm_master_be=load_be;
        force dut.instr_req=fetch_req;force dut.instr_addr=fetch_addr;
        #1;rst_n=0;repeat(12) @(negedge clk);rst_n=1;
        repeat(20) @(negedge clk);
        for(integer n=0;n<24;n=n+1) sba_write(32'h80000100+4*n,32'h11220000+n,15);
        fetch(32'h80000104,32'h11220001);
        fetch(32'h80000104,32'h11220001,1);
        fetch(32'h80000124,32'h11220009);
        sba_write(32'h80000180,32'h88888888,15);
        fetch(32'h80000104,32'h11220001,1);
        fetch(32'h80000124,32'h11220009,1);
        sba_write(32'h80000104,32'hffffffff,0);
        fetch(32'h80000104,32'h11220001,1);
        sba_write(32'h80002104,32'h0000bb00,2);
        fetch(32'h80000104,32'h1122bb01);
        fetch(32'h80000124,32'h11220009,1);
        fetch(32'h80002104,32'h1122bb01);
        sba_write(32'h80000104,32'hcafebabe,15);
        fetch(32'h80002104,32'hcafebabe);
        fetch(32'h80000104,32'hcafebabe);
        sba_write(32'h80006104,32'hffffffff,0);
        fetch(32'h80000104,32'hcafebabe,1);
        sba_write(32'h0001003c,32'hbad00000,15);
        fetch(32'h80000104,32'hcafebabe,2);
        if(dut.boot_ready || alias_writes!=1 || zero_strobes!=2)
            $fatal(1,"SNOOP_SOC_FAIL insufficient coverage or unintended boot");
        $display("IFETCH_SNOOP_SOC PASS checks=%0d accepted_writes=%0d alias_writes=%0d zero_strobes=%0d",checks,accepted_writes,alias_writes,zero_strobes);
        $finish;
    end
    initial begin #1000000;$fatal(1,"SNOOP_SOC_FAIL watchdog");end
endmodule
