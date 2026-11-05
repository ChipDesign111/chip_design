`timescale 1ns/1ps
// Probe bench: same boot as tb_lat, but prints the per-cycle handshake of the
// DM adapter / crossbar / axi2mem chain while the image is being streamed, so
// the measured 3 cycles/word can be attributed to a specific stage.
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
    integer resp_count=0,resp_base=0;
    integer probe=0;
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
    always @(posedge clk) if(dut.dm_master_r_valid===1'b1) resp_count=resp_count+1;
    task automatic stream_image(input integer first,input integer count);
        integer k;
        begin
            @(negedge clk);
            load_req=1;load_we=1;load_be=4'hf;
            load_addr=32'h80000000+first*4;load_data=image[first];
            for(k=first;k<first+count;k=k+1) begin
                @(posedge clk);
                while(dut.dm_master_gnt!==1'b1) @(posedge clk);
                if(k+1<first+count) begin
                    @(negedge clk);
                    load_addr=32'h80000000+(k+1)*4;load_data=image[k+1];
                end
            end
            @(negedge clk);load_req=0;
        end
    endtask
    always @(posedge clk) if(dut.sram_req && dut.sram_we && dut.sram_addr==32'h80001fe0) magic<=dut.sram_wdata;
    always @(negedge clk) if(probe>0 && probe<40) begin
        probe=probe+1;
        $display("P%0d t=%0t ad=%0d oc=%0d req=%b gnt=%b | slv2 awv=%b awr=%b wv=%b wr=%b bv=%b | sram req=%b we=%b a=%h | a2m=%0d bwv=%b",
                 probe,$time,
                 dut.i_axi_adapter_dm.state_q, dut.i_axi_adapter_dm.outstanding_aw_cnt_q,
                 dut.dm_master_req, dut.dm_master_gnt,
                 dut.slave[2].aw_valid, dut.slave[2].aw_ready,
                 dut.slave[2].w_valid,  dut.slave[2].w_ready, dut.slave[2].b_valid,
                 dut.sram_req, dut.sram_we, dut.sram_addr,
                 dut.i_axi2sram.state_q, dut.i_axi2sram.slave.b_valid);
    end else if(probe==40) probe=41;
    integer i;
    initial begin
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
        resp_base=resp_count;
        stream_image(0,32);
        while(resp_count<resp_base+32) @(negedge clk);
        sba_write(32'h0001003c,32'hb007c0de,15);
        probe=1;
        resp_base=resp_count;
        stream_image(32,2016);
        probe=41;
        while(resp_count<resp_base+2016) @(negedge clk);
        sba_write(32'h0001003c,32'hdeadbeef,15);
        repeat(8) @(negedge clk);
        sba_write(32'h0001003c,32'hb007c0de,15);
        while(cycles<200000 && magic!==32'hc0dec0de) begin
            @(negedge clk);cycles=cycles+1;
            if(magic===32'hdeadbeef) $fatal(1,"CPU numerical self-check failed");
        end
        if(magic!==32'hc0dec0de) $fatal(1,"SoC timeout, PC=%h",dut.instr_addr);
        $display("INT8_SOC PASS cycles=%0d",cycles);
        $finish;
    end
endmodule
