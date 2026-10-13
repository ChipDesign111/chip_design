`timescale 1ns/1ps
module tb_har_core;
    logic clk=0,rst_ni=0,start=0,ack_done=0,batch_two=0;
    always #5 clk=~clk;
    logic [511:0] x,x1;
    logic [1023:0] b1;
    logic [191:0] b2;
    logic [15:0] mult;
    logic [4:0] shift;
    wire busy,done;
    wire [255:0] hidden,hidden1;
    wire [191:0] scores,scores1;
    wire [2:0] category,category1;
    wire [31:0] cycles,overlap,fc1_cycles,fc2_cycles;
    logic cpu_we=0;
    logic [9:0] cpu_addr=0;
    logic [31:0] cpu_data=0;
    wire w1_re,w2_re;
    wire [3:0] w1_addr;
    wire [2:0] w2_addr;
    wire [1023:0] w1_data;
    wire [191:0] w2_data;
    har_weight_store store(.clk(clk),.rst_ni(rst_ni),.cpu_we(cpu_we),.cpu_re(1'b0),
        .cpu_addr(cpu_addr),.cpu_wdata(cpu_data),.cpu_rdata(),
        .fc1_re(w1_re),.fc1_addr(w1_addr),.fc1_data(w1_data),
        .fc2_re(w2_re),.fc2_addr(w2_addr),.fc2_data(w2_data));
    har_npu_core dut(.clk(clk),.rst_ni(rst_ni),.start(start),.ack_done(ack_done),.batch_two(batch_two),
        .input_features(x),.input_features1(x1),.bias1(b1),.bias2(b2),
        .requant_mult(mult),.requant_shift(shift),.busy(busy),.done(done),
        .hidden(hidden),.hidden1(hidden1),.scores(scores),.scores1(scores1),
        .class_id(category),.class_id1(category1),.cycle_count(cycles),
        .overlap_count(overlap),.fc1_cycles(fc1_cycles),.fc2_cycles(fc2_cycles),
        .w1_re(w1_re),.w1_addr(w1_addr),.w1_data(w1_data),
        .w2_re(w2_re),.w2_addr(w2_addr),.w2_data(w2_data));
    localparam WORDS=2383;
    reg [31:0] vector_mem[0:1000*WORDS-1],batch_mem[0:1000*103-1];
    string vector_file,batch_file;
    integer count=1000,c,i,p,q,elapsed,mode,observed_overlap;
    reg [255:0] saved_hidden;
    reg [191:0] saved_scores;
    task load_case(input integer n);
        integer j;
        begin
            p=n*WORDS;q=n*103;
            for(j=0;j<64;j=j+1) begin x[j*8+:8]=vector_mem[p+j][7:0];x1[j*8+:8]=batch_mem[q+j][7:0];end
            for(j=0;j<32;j=j+1) b1[j*32+:32]=vector_mem[p+2304+j];
            for(j=0;j<6;j=j+1) b2[j*32+:32]=vector_mem[p+2336+j];
            mult=vector_mem[p+2342][15:0];shift=vector_mem[p+2343][4:0];
            for(j=0;j<560;j=j+1) begin
                @(negedge clk);cpu_we=1;cpu_addr=j;
                cpu_data={vector_mem[p+64+j*4+3][7:0],vector_mem[p+64+j*4+2][7:0],
                          vector_mem[p+64+j*4+1][7:0],vector_mem[p+64+j*4][7:0]};
            end
            @(negedge clk);cpu_we=0;
        end
    endtask
    task check_first;
        begin
            for(i=0;i<32;i=i+1)
                if(hidden[i*8+:8]!==vector_mem[p+2344+i][7:0]) $fatal(1,"Hidden case %0d index %0d got %d expected %d",c,i,hidden[i*8+:8],vector_mem[p+2344+i]);
            for(i=0;i<6;i=i+1)
                if(scores[i*32+:32]!==vector_mem[p+2376+i]) $fatal(1,"Score case %0d index %0d",c,i);
            if(category!==vector_mem[p+2382][2:0]) $fatal(1,"Class case %0d",c);
        end
    endtask
    initial begin
        if(!$value$plusargs("VECTORS=%s",vector_file) || !$value$plusargs("BATCH=%s",batch_file)) $fatal(1,"Missing vectors");
        if($value$plusargs("COUNT=%d",count)) begin end
        if(count<12 || count>1000) $fatal(1,"Invalid count");
        $readmemh(vector_file,vector_mem,0,count*WORDS-1);
        $readmemh(batch_file,batch_mem,0,count*103-1);
        repeat(3) @(negedge clk);rst_ni=1;
        // Abort during FC1, FC2, and actual two-sample overlap; reload afterward.
        load_case(0);
        for(mode=0;mode<3;mode=mode+1) begin
            batch_two=mode==2;
            @(negedge clk);start=1;
            @(negedge clk);start=0;
            repeat(mode==0 ? 10:25) @(negedge clk);
            rst_ni=0;#1;
            if(busy!==0 || done!==0 || hidden!==0 || scores!==0 || overlap!==0) $fatal(1,"Pipeline reset");
            @(negedge clk);rst_ni=1;
        end
        for(c=0;c<count;c=c+1) begin
            load_case(c);
            for(mode=0;mode<2;mode=mode+1) begin
                batch_two=mode;
                @(negedge clk);start=1;
                @(negedge clk);start=0;
                if(done!==0 || busy!==1) $fatal(1,"START handshake");
                elapsed=0;observed_overlap=0;
                while(done!==1 && elapsed<100) begin
                    if(dut.s1_active && dut.s2_active) observed_overlap=observed_overlap+1;
                    @(negedge clk);elapsed=elapsed+1;
                    start=elapsed==5;ack_done=elapsed==7;
                end
                start=0;ack_done=0;
                if(done!==1 || busy!==0) $fatal(1,"Timeout case %0d",c);
                check_first();
                if(cycles!==(mode==0 ? 39:59) || cycles!==elapsed)
                    $fatal(1,"Cycle case %0d mode %0d got %0d elapsed %0d",c,mode,cycles,elapsed);
                if(fc1_cycles!==(mode==0 ? 19:38) || fc2_cycles!==(mode==0 ? 19:38)) $fatal(1,"Unbalanced stage counters");
                if(overlap!==(mode==0 ? 0:18) || overlap!==observed_overlap) $fatal(1,"No real overlap");
                if(mode==1) begin
                    for(i=0;i<32;i=i+1)
                        if(hidden1[i*8+:8]!==batch_mem[q+64+i][7:0]) $fatal(1,"Batch hidden case %0d index %0d",c,i);
                    for(i=0;i<6;i=i+1)
                        if(scores1[i*32+:32]!==batch_mem[q+96+i]) $fatal(1,"Batch scores case %0d index %0d",c,i);
                    if(category1!==batch_mem[q+102][2:0]) $fatal(1,"Batch class");
                end
                saved_hidden=hidden;saved_scores=scores;
                repeat(3) @(negedge clk);
                if(done!==1 || hidden!==saved_hidden || scores!==saved_scores) $fatal(1,"Not sticky");
                // Single -> batch restarts directly from sticky DONE, without ACK.
                if(mode==1) begin
                    @(negedge clk);ack_done=1;
                    @(negedge clk);ack_done=0;
                    if(done!==0 || busy!==0) $fatal(1,"ACK");
                end
            end
            if((c+1)%250==0) $display("HAR_CORE progress %0d/%0d",c+1,count);
        end
        $display("HAR_CORE PASS cases=%0d inferences=%0d single=39 batch2=59 overlap=18 stage_balance=19/19 reset/busy/sticky/ack=PASS",count,count*3);
        $finish;
    end
endmodule
