`timescale 1ns/1ps
// Online host model at the Debug SBA request boundary. Transactions traverse
// real AXI arbitration, SRAM, CPU and NPU; this is not serial JTAG wire testing.
module tb_live_demo;
    `include "live_config.svh"
    reg clk=0,rst_n=0;
    always #5 clk=~clk;
    wire tdo;
    my_soc_top dut(.clk_i(clk),.rst_ni(rst_n),.tck_i(1'b0),.tms_i(1'b0),.td_i(1'b0),.td_o(tdo));
    reg load_req=0,load_we=0;
    reg [3:0] load_be=15;
    reg [31:0] load_addr=0,load_data=0;
    reg [31:0] image[0:2047];
    localparam [31:0] MB=32'h80001fc0;
    reg [31:0] inputs[0:ROUNDS*INPUT_WORDS-1];
    reg [31:0] expected[0:ROUNDS*OUTPUT_WORDS-1];
    reg [31:0] expected_class[0:ROUNDS-1];
    reg [31:0] observed,status,error,result_seq,last_output;
    integer npu_starts=0,activation_writes=0;
    reg inference_active=0;
    reg [31:0] expected_hidden[0:ROUNDS*HIDDEN_WORDS-1];
    integer i,r,w,timeout,initial_starts,request_seq;
    always @(posedge clk) begin
        if(dut.ndmreset_n && !dut.boot_ready && dut.instr_req)
            $fatal(1,"CPU fetched before firmware commit");
        if(dut.i_npu_subsystem.i_npu_core.start) npu_starts<=npu_starts+1;
        if(inference_active && dut.sram_req && dut.sram_we &&
           dut.sram_addr>=HIDDEN_ADDRESS && dut.sram_addr<HIDDEN_ADDRESS+HIDDEN_WORDS*4)
            activation_writes<=activation_writes+1;
    end
    task sba_write(input reg [31:0] address,value,input reg [3:0] be);
        integer t;
        begin
            @(negedge clk);load_req=1;load_we=1;load_addr=address;load_data=value;load_be=be;t=0;
            @(posedge clk);
            while(!dut.dm_master_gnt && t<1000) begin @(posedge clk);t=t+1;end
            if(t>=1000) $fatal(1,"SBA write grant timeout");
            @(negedge clk);load_req=0;t=0;
            while(!dut.dm_master_r_valid && t<1000) begin @(posedge clk);t=t+1;end
            if(t>=1000) $fatal(1,"SBA write response timeout");
            @(negedge clk);
        end
    endtask
    task sba_read(input reg [31:0] address,output reg [31:0] value);
        integer t;
        begin
            @(negedge clk);load_req=1;load_we=0;load_addr=address;load_be=15;t=0;
            @(posedge clk);
            while(!dut.dm_master_gnt && t<1000) begin @(posedge clk);t=t+1;end
            if(t>=1000) $fatal(1,"SBA read grant timeout");
            @(negedge clk);load_req=0;t=0;
            while(!dut.dm_master_r_valid && t<1000) begin @(posedge clk);t=t+1;end
            if(t>=1000) $fatal(1,"SBA read response timeout");
            value=dut.dm_master_r_rdata;
            @(negedge clk);
        end
    endtask
    task await_response(input integer seq,expected_status,expected_error);
        integer t;
        begin
            t=0;result_seq=0;
            while(result_seq!==seq && t<10000) begin
                sba_read(MB+12,result_seq);t=t+1;
            end
            if(result_seq!==seq) $fatal(1,"Response timeout seq=%0d PC=%h",seq,dut.instr_addr);
            sba_read(MB+24,status);sba_read(MB+28,error);
            if(status!==expected_status || error!==expected_error)
                $fatal(1,"Wrong response seq=%0d status=%h error=%h",seq,status,error);
            sba_read(MB+32,observed);
            if(observed==0 || ^observed===1'bx) $fatal(1,"No valid real CPU mcycle measurement");
            $display("LIVE_RESPONSE seq=%0d status=%0d error=%0d cycles=%0d",$unsigned(seq),status,error,observed);
        end
    endtask
    initial begin
        force dut.dm_master_req=load_req;force dut.dm_master_we=load_we;
        force dut.dm_master_add=load_addr;force dut.dm_master_wdata=load_data;force dut.dm_master_be=load_be;
        $readmemh("firmware.hex",image);$readmemh("input_vectors.hex",inputs);
        $readmemh("expected_vectors.hex",expected);$readmemh("expected_hidden.hex",expected_hidden);$readmemh("expected_classes.hex",expected_class);
        #1;rst_n=0;repeat(12) @(negedge clk);rst_n=1;
        repeat(30) @(negedge clk);
        for(i=0;i<2048;i=i+1) sba_write(32'h80000000+i*4,image[i],15);
        if(dut.boot_ready) $fatal(1,"Boot did not require explicit commit");
        sba_write(32'h0001003c,32'hb007c0de,15);
        timeout=0;status=0;
        while(status!==1 && timeout<1000) begin sba_read(MB+24,status);timeout=timeout+1;end
        if(status!==1) $fatal(1,"Resident did not become READY");
        sba_read(MB,observed);if(observed!==32'h4c495645)$fatal(1,"Resident magic mismatch");
        sba_read(MB+4,observed);if(observed!==1)$fatal(1,"Resident ABI mismatch");
        sba_read(MB+48,observed);if(observed!==INPUT_ADDRESS)$fatal(1,"Input address mismatch");
        sba_read(MB+52,observed);if(observed!==OUTPUT_ADDRESS)$fatal(1,"Output address mismatch");
        sba_read(MB+56,observed);if(observed!==PACKAGE_TAG_LOW)$fatal(1,"Model identity mismatch");
        sba_read(MB+60,observed);if(observed!==PACKAGE_TAG_HIGH)$fatal(1,"Model identity mismatch");
        if(npu_starts!=0) $fatal(1,"Model ran before live request");
        request_seq=1;
        for(r=0;r<ROUNDS;r=r+1) begin
            // Same boot, no halt/reset/model reload between any requests.
            for(w=0;w<INPUT_WORDS;w=w+1)
                sba_write(INPUT_ADDRESS+w*4,inputs[r*INPUT_WORDS+w],15);
            sba_write(MB+16,1,15);sba_write(MB+20,INPUT_BYTES,15);
            inference_active=1;
            sba_write(MB+8,request_seq,15);
            await_response(request_seq,3,0);
            inference_active=0;
            for(w=0;w<HIDDEN_WORDS;w=w+1) begin
                sba_read(HIDDEN_ADDRESS+w*4,observed);
                if(observed!==expected_hidden[r*HIDDEN_WORDS+w])
                    $fatal(1,"Live hidden activation mismatch round=%0d word=%0d got=%h",r,w,observed);
            end
            for(w=0;w<OUTPUT_WORDS;w=w+1) begin
                sba_read(OUTPUT_ADDRESS+w*4,observed);
                if((observed & (w==OUTPUT_WORDS-1 ? OUTPUT_TAIL_MASK : 32'hffffffff))!==
                   expected[r*OUTPUT_WORDS+w])
                    $fatal(1,"Live output mismatch round=%0d word=%0d actual=%h expected=%h",r,w,observed,expected[r*OUTPUT_WORDS+w]);
                $display("LIVE_OUTPUT round=%0d word=%0d actual=%08x",r,w,observed);
            end
            sba_read(MB+40,observed);
            if(observed!==expected_class[r]) $fatal(1,"Real CPU argmax mismatch round=%0d",r);
            sba_read(MB+36,observed);
            if(observed!==r+1) $fatal(1,"Execution count mismatch");
            if(npu_starts!=(r+1)*NPU_STARTS_PER_ROUND)
                $fatal(1,"Wrong real RAW NPU count %0d",npu_starts);
            initial_starts=npu_starts;
            // Duplicate commit must neither run again nor alter completion.
            sba_write(MB+8,request_seq,15);repeat(300) @(negedge clk);
            sba_read(MB+36,observed);
            if(observed!==r+1 || npu_starts!=initial_starts) $fatal(1,"Duplicate sequence reexecuted");
            request_seq=request_seq+1;
            if(r==0) begin
                // A rejected length and a rejected command must not launch NPU.
                sba_write(MB+20,INPUT_BYTES-1,15);sba_write(MB+8,request_seq,15);
                await_response(request_seq,4,2);request_seq=request_seq+1;
                sba_write(MB+20,INPUT_BYTES,15);sba_write(MB+16,99,15);
                sba_write(MB+8,request_seq,15);await_response(request_seq,4,1);
                if(npu_starts!=initial_starts) $fatal(1,"Rejected request launched NPU");
                request_seq=request_seq+1;
            end
            if(r==1) request_seq=32'hffffffff;
            if(r==2) begin
                // Zero is never a commit, and uint32 sequence rollover skips it.
                sba_write(MB+8,0,15);repeat(300) @(negedge clk);
                sba_read(MB+12,observed);
                if(observed!==32'hffffffff || npu_starts!=initial_starts)
                    $fatal(1,"Zero sequence was accepted during rollover");
                request_seq=1;
                $display("LIVE_SEQUENCE_WRAP PASS max_seq=4294967295 zero_ignored=1");
            end
        end
        if(activation_writes==0) $fatal(1,"No actual dynamic hidden writeback observed");
        $display("LIVE_DEMO PASS rounds=%0d npu_starts=%0d activation_writes=%0d duplicate_requests=%0d rejected_requests=2",ROUNDS,npu_starts,activation_writes,ROUNDS);
        $finish;
    end
    initial begin
        #100000000;
        $fatal(1,"Global live demo watchdog");
    end
endmodule
