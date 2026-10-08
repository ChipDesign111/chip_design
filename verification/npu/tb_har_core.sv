`timescale 1ns/1ps
module tb_har_core;
    logic clk=0, rst_ni=0, start=0, ack_done=0;
    always #5 clk=~clk;
    logic [511:0] x;
    logic [16383:0] w1;
    logic [1535:0] w2;
    logic [1023:0] b1;
    logic [191:0] b2;
    logic [15:0] mult;
    logic [4:0] shift;
    wire busy,done;
    wire [255:0] hidden;
    wire [191:0] scores;
    wire [2:0] category;
    wire [31:0] cycles;
    har_npu_core dut(.clk(clk),.rst_ni(rst_ni),.start(start),.ack_done(ack_done),
        .input_features(x),.weight1(w1),.weight2(w2),.bias1(b1),.bias2(b2),
        .requant_mult(mult),.requant_shift(shift),.busy(busy),.done(done),
        .hidden(hidden),.scores(scores),.class_id(category),.cycle_count(cycles));
    localparam WORDS=2383;
    reg [31:0] vector_mem [0:1000*WORDS-1];
    string vector_file;
    integer count=1000, c,i,p,elapsed;
    reg [255:0] saved_hidden;
    reg [191:0] saved_scores;
    task load_case(input integer n);
        begin
            p=n*WORDS;
            for(i=0;i<64;i=i+1) x[i*8+:8]=vector_mem[p+i][7:0]; p=p+64;
            for(i=0;i<2048;i=i+1) w1[i*8+:8]=vector_mem[p+i][7:0]; p=p+2048;
            for(i=0;i<192;i=i+1) w2[i*8+:8]=vector_mem[p+i][7:0]; p=p+192;
            for(i=0;i<32;i=i+1) b1[i*32+:32]=vector_mem[p+i]; p=p+32;
            for(i=0;i<6;i=i+1) b2[i*32+:32]=vector_mem[p+i]; p=p+6;
            mult=vector_mem[p][15:0]; shift=vector_mem[p+1][4:0]; p=p+2;
        end
    endtask
    initial begin
        if (!$value$plusargs("VECTORS=%s",vector_file)) $fatal(1,"Missing vector file");
        if ($value$plusargs("COUNT=%d",count)) begin end
        if (count<12 || count>1000) $fatal(1,"Invalid count");
        $readmemh(vector_file,vector_mem,0,count*WORDS-1);
        repeat(3) @(negedge clk); rst_ni=1;
        load_case(0);
        @(negedge clk); start=1;
        @(negedge clk); start=0;
        repeat(20) @(negedge clk);
        rst_ni=0; #1;
        if(busy!==0 || done!==0 || hidden!==0 || scores!==0) $fatal(1,"Reset during inference");
        @(negedge clk); rst_ni=1;
        for(c=0;c<count;c=c+1) begin
            load_case(c);
            @(negedge clk); start=1;
            @(negedge clk); start=0;
            if(done!==0 || busy!==1) $fatal(1,"START handshake case %0d",c);
            elapsed=0;
            while(done!==1 && elapsed<2400) begin
                @(negedge clk); elapsed=elapsed+1;
                // A core START/ACK while busy must not restart the calculation.
                start=(elapsed==5); ack_done=(elapsed==7);
            end
            start=0; ack_done=0;
            if(done!==1 || busy!==0) $fatal(1,"Timeout case %0d",c);
            for(i=0;i<32;i=i+1)
                if(hidden[i*8+:8] !== vector_mem[p+i][7:0]) $fatal(1,"Hidden mismatch case %0d item %0d",c,i);
            for(i=0;i<6;i=i+1)
                if(scores[i*32+:32] !== vector_mem[p+32+i]) $fatal(1,"Score mismatch case %0d item %0d",c,i);
            if(category !== vector_mem[p+38][2:0]) $fatal(1,"Class mismatch case %0d",c);
            if(cycles!==2279) $fatal(1,"Cycle counter contract case %0d got %0d",c,cycles);
            saved_hidden=hidden; saved_scores=scores;
            x='0; w1='0; w2='0;
            repeat(3) @(negedge clk);
            if(done!==1 || hidden!==saved_hidden || scores!==saved_scores) $fatal(1,"Result/DONE not sticky");
            @(negedge clk); ack_done=1;
            @(negedge clk); ack_done=0;
            if(done!==0 || busy!==0) $fatal(1,"ACK did not clear DONE");
            if((c+1)%250==0) $display("HAR_CORE progress %0d/%0d",c+1,count);
        end
        $display("HAR_CORE PASS cases=%0d cycles=2279 reset/busy/sticky/ack=PASS",count);
        $finish;
    end
endmodule
