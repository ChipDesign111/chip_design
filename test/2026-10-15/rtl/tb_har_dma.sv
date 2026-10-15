`timescale 1ns/1ps
module tb_har_dma;
    reg clk=0, rst_n=0;
    always #5 clk=~clk;
    reg req=0,we=0,npu_busy=0,conflict=0;
    reg [4:0] reg_addr=0;
    reg [31:0] reg_data=0;
    wire [31:0] reg_result, ar_addr,aw_addr,w_data;
    wire [7:0] ar_len,aw_len;
    wire busy,ar_valid,aw_valid,r_ready,w_valid,w_last,b_ready;
    reg ar_ready=0,aw_ready=0,w_ready=0,r_valid=0,r_last=0,b_valid=0;
    reg [31:0] r_data=0;
    reg [1:0] r_resp=0,b_resp=0;
    har_dma dut(.clk_i(clk),.rst_ni(rst_n),.reg_req_i(req),.reg_we_i(we),
        .reg_addr_i(reg_addr),.reg_wdata_i(reg_data),.reg_rdata_o(reg_result),
        .npu_busy_i(npu_busy),.conflict_i(conflict),.busy_o(busy),
        .ar_addr_o(ar_addr),.ar_len_o(ar_len),.ar_valid_o(ar_valid),.ar_ready_i(ar_ready),
        .aw_addr_o(aw_addr),.aw_len_o(aw_len),.aw_valid_o(aw_valid),.aw_ready_i(aw_ready),
        .r_data_i(r_data),.r_resp_i(r_resp),.r_last_i(r_last),.r_valid_i(r_valid),.r_ready_o(r_ready),
        .w_data_o(w_data),.w_last_o(w_last),.w_valid_o(w_valid),.w_ready_i(w_ready),
        .b_resp_i(b_resp),.b_valid_i(b_valid),.b_ready_o(b_ready));
    reg [31:0] source[0:2047], target[0:1023], pending[0:15];
    reg read_active=0,aw_seen=0,w_seen=0;
    reg [31:0] rng=32'h54cafe12;
    integer read_index=0,read_base=0,read_beats=0,write_base=0,write_beats=0,write_index=0;
    integer fault=0,transfers=0,ar_count=0,aw_count=0;
    integer i,n,s,d,mode,timeout,b;
    reg ar_stalled=0,aw_stalled=0,w_stalled=0;
    reg [39:0] held_ar,held_aw;
    reg [32:0] held_w;
    reg [31:0] status,value;
    function automatic [31:0] random_word(input [31:0] in);
        reg [31:0] x;
        x=in^(in<<13);x=x^(x>>17);return x^(x<<5);
    endfunction
    // Independent AXI responder with deterministic random channel stalls.
    always @(negedge clk) begin
        rng=random_word(rng);
        ar_ready=rst_n && !read_active && rng[0];
        aw_ready=rst_n && !aw_seen && rng[1];
        // Accept W before AW as well, exercising independent write channels.
        w_ready=rst_n && !w_seen && rng[2];
        if(!rst_n) begin r_valid=0;b_valid=0;end
        else begin
            if(!r_valid || r_ready) begin
                r_valid=read_active && rng[3];
                r_data=source[(read_base+read_index)%2048];
                r_resp=fault==1 && read_index==0 ? 2'b10:2'b00;
                r_last=read_index==(read_beats-1+(fault==4 ? 1:0)-(fault==3 && read_beats>1 ? 1:0));
            end
            if(!b_valid || b_ready) begin
                b_valid=aw_seen && w_seen && rng[4];
                b_resp=fault==2 ? 2'b10:2'b00;
            end
        end
    end
    always @(posedge clk) begin
        if(!rst_n) begin
            read_active=0;aw_seen=0;w_seen=0;read_index=0;write_index=0;
            ar_stalled=0;aw_stalled=0;w_stalled=0;
        end else begin
            if(ar_stalled && (!ar_valid || {ar_addr,ar_len}!==held_ar)) $fatal(1,"AR changed under stall");
            if(aw_stalled && (!aw_valid || {aw_addr,aw_len}!==held_aw)) $fatal(1,"AW changed under stall");
            if(w_stalled && (!w_valid || {w_data,w_last}!==held_w)) $fatal(1,"W changed under stall");
            ar_stalled=ar_valid && !ar_ready;held_ar={ar_addr,ar_len};
            aw_stalled=aw_valid && !aw_ready;held_aw={aw_addr,aw_len};
            w_stalled=w_valid && !w_ready;held_w={w_data,w_last};
            if(ar_valid && ar_ready) begin
                if(ar_addr[1:0]!=0 || ar_len>15 || {1'b0,ar_addr[11:0]}+((ar_len+1)*4)>4096)
                    $fatal(1,"Invalid/cross-page read burst");
                read_active=1;read_index=0;read_base=(ar_addr-32'h80000000)/4;
                read_beats=ar_len+1;ar_count=ar_count+1;
            end
            if(r_valid && r_ready) begin
                read_index=read_index+1;
                if(r_last) read_active=0;
            end
            if(aw_valid && aw_ready) begin
                if(aw_addr[1:0]!=0 || aw_len>15 || {1'b0,aw_addr[11:0]}+((aw_len+1)*4)>4096)
                    $fatal(1,"Invalid/cross-page write burst");
                aw_seen=1;write_base=(aw_addr-32'h70000000)/4;write_beats=aw_len+1;aw_count=aw_count+1;
            end
            if(w_valid && w_ready) begin
                if(write_index>=16) $fatal(1,"Write overflow");
                pending[write_index]=w_data;write_index=write_index+1;
                if(w_last) w_seen=1;
            end
            if(aw_seen && w_seen && write_index!=write_beats) $fatal(1,"WLAST/length mismatch");
            if(b_valid && b_ready) begin
                for(b=0;b<16;b=b+1)
                    if(b<write_beats) target[write_base+b]=pending[b];
                aw_seen=0;w_seen=0;write_index=0;
            end
        end
    end
    task automatic write_reg(input [4:0] address,input [31:0] data);
        @(negedge clk);req=1;we=1;reg_addr=address;reg_data=data;
        @(posedge clk);#1;@(negedge clk);req=0;we=0;
    endtask
    task automatic read_reg(input [4:0] address,output [31:0] data);
        @(negedge clk);req=1;we=0;reg_addr=address;
        @(posedge clk);#1;data=reg_result;@(negedge clk);req=0;
    endtask
    task automatic configure(input [31:0] src,dst,input integer count);
        write_reg(8,src);write_reg(12,dst);write_reg(16,count);write_reg(0,1);
    endtask
    task automatic wait_done(input bit expected_error);
        integer limit;
        reg [31:0] st;
        begin
            limit=0;st=0;
            while(!st[0] && limit<20000) begin read_reg(4,st);limit=limit+1;end
            if(!st[0] || st[1] || st[2]!=expected_error) $fatal(1,"DMA status %h expected_error=%0d",st,expected_error);
            transfers=transfers+1;
        end
    endtask
    task automatic good_copy(input integer src,dst,count,input bit expected_error);
        integer k;
        begin
            configure(32'h80000000+src*4,32'h70000000+dst*4,count);
            wait_done(expected_error);
            read_reg(24,value);if(value!=count) $fatal(1,"Copied count mismatch");
            read_reg(20,value);if(value==0) $fatal(1,"Missing DMA cycle count");
            for(k=0;k<count;k=k+1)
                if(target[dst+k]!==source[src+k]) $fatal(1,"DMA data mismatch index=%0d",k);
        end
    endtask
    initial begin
        for(i=0;i<2048;i=i+1) source[i]=32'h12345678^(i*32'h10204081);
        for(i=0;i<1024;i=i+1) target[i]=32'hdeadbeef;
        repeat(3) @(negedge clk);rst_n=1;
        // Tail lengths and 4 KiB source splitting.
        for(i=0;i<9;i=i+1) begin
            case(i) 0:n=1;1:n=2;2:n=15;3:n=16;4:n=17;5:n=31;6:n=32;7:n=33;8:n=598;endcase
            good_copy(1020,64,n,0);
        end
        good_copy(2032,16,16,0);good_copy(0,768,16,0);
        for(i=0;i<200;i=i+1) begin
            n=(rng%598)+1;s=(rng>>10)%(2049-n);d=64+(rng>>20)%(599-n);
            good_copy(s,d,n,0);
        end
        // Rejected configurations must emit no AXI requests.
        s=ar_count;
        configure(32'h80000001,32'h70000100,1);wait_done(1);
        configure(32'h80001ffc,32'h70000100,2);wait_done(1);
        configure(32'h80000000,32'h70000000,1);wait_done(1);
        configure(32'h80000000,32'h70000a54,2);wait_done(1);
        configure(32'h80000000,32'h70000100,0);wait_done(1);
        configure(32'h80000000,32'h70000100,32'hffffffff);wait_done(1);
        npu_busy=1;configure(32'h80000000,32'h70000100,1);wait_done(1);npu_busy=0;
        if(ar_count!=s) $fatal(1,"Rejected request reached AXI");
        for(mode=1;mode<=4;mode=mode+1) begin
            fault=mode;configure(32'h80000000,32'h70000100,16);wait_done(1);
            read_reg(24,value);if(value!=0) $fatal(1,"Failed burst counted successful");
        end
        fault=0;
        configure(32'h80000000,32'h70000100,598);
        write_reg(8,32'h80001ffc);write_reg(0,1);write_reg(0,2);
        @(negedge clk);conflict=1;@(negedge clk);conflict=0;
        wait_done(1);read_reg(24,value);if(value!=598) $fatal(1,"Busy writes corrupted transfer");
        for(i=0;i<598;i=i+1) if(target[64+i]!==source[i]) $fatal(1,"Conflict changed DMA data");
        // Reset both endpoints in each externally active channel phase.
        for(mode=2;mode<=5;mode=mode+1) begin
            configure(32'h80000000,32'h70000100,16);
            timeout=0;
            while(dut.state!=mode && timeout<1000) begin @(negedge clk);timeout=timeout+1;end
            if(timeout==1000) $fatal(1,"Missing reset phase");
            rst_n=0;repeat(2) @(negedge clk);rst_n=1;
            read_reg(4,status);if(status!=0) $fatal(1,"Reset failed");
            good_copy(0,64,16,0);
        end
        $display("DMA_UNIT PASS transfers=%0d randomized=200 faults=4 reset_phases=4",transfers);
        $finish;
    end
    initial begin #30000000;$fatal(1,"DMA test timeout");end
endmodule
