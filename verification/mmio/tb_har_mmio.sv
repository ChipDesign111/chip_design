`timescale 1ns/1ps
module tb_har_mmio;
    logic clk=0,rst_ni=0,ena=0,wea=0;
    logic [11:0] addr=0;
    logic [31:0] data=0;
    wire [31:0] result;
    always #5 clk=~clk;
    simple_npu_top dut(.clka(clk),.rst_ni(rst_ni),.ena(ena),.wea(wea),.addra(addr),.dina(data),.douta(result));
    localparam WORDS=2383;
    reg [31:0] vector_mem[0:12*WORDS-1];
    reg [31:0] batch_mem[0:1000*103-1];
    string path,batch_path;
    integer c,i,p,elapsed;
    reg [31:0] r,packed_word,original_input;
    task write_word(input integer a,input reg[31:0] d);
        begin @(negedge clk);ena=1;wea=1;addr=a;data=d;
            @(negedge clk);ena=0;wea=0; end
    endtask
    task read_word(input integer a,output reg[31:0] d);
        begin @(negedge clk);ena=1;wea=0;addr=a;
            @(posedge clk);#1;d=result;
            @(negedge clk);ena=0; end
    endtask
    task load_bytes(input integer source,input integer destination,input integer length);
        integer n;
        reg[31:0] word_value;
        begin for(n=0;n<length;n=n+4) begin
            word_value={vector_mem[source+n+3][7:0],vector_mem[source+n+2][7:0],
                        vector_mem[source+n+1][7:0],vector_mem[source+n][7:0]};
            write_word(destination+n/4,word_value);
            read_word(destination+n/4,r);
            if(r!==word_value) $fatal(1,"Packed readback %0d",destination+n/4);
        end end
    endtask
    initial begin
        if(!$value$plusargs("VECTORS=%s",path)) $fatal(1,"Missing vector file");
        $readmemh(path,vector_mem);
        if(!$value$plusargs("BATCH=%s",batch_path)) $fatal(1,"Missing batch vectors");
        $readmemh(batch_path,batch_mem,0,12*103-1);
        repeat(3) @(negedge clk);rst_ni=1;
        // Bad configuration is rejected and reported.
        write_word(4,65536);write_word(5,32);read_word(1,r);
        if(r[2]!==1) $fatal(1,"Invalid config not reported");
        read_word(4,r);if(r!==1) $fatal(1,"Invalid multiplier accepted");
        read_word(5,r);if(r!==0) $fatal(1,"Invalid shift accepted");
        write_word(0,2);
        write_word(6,0);write_word(6,3);read_word(6,r);if(r!==1) $fatal(1,"Invalid batch accepted");
        read_word(1,r);if(r[2]!==1) $fatal(1,"Invalid batch not reported");write_word(0,2);
        for(c=0;c<12;c=c+1) begin
            p=c*WORDS;
            load_bytes(p,16,64);
            load_bytes(p+64,64,2048);
            load_bytes(p+2112,576,192);
            for(i=0;i<32;i=i+1) write_word(624+i,vector_mem[p+2304+i]);
            for(i=0;i<6;i=i+1) write_word(656+i,vector_mem[p+2336+i]);
            write_word(4,vector_mem[p+2342]);write_word(5,vector_mem[p+2343]);
            read_word(16,original_input);
            write_word(0,1);
            write_word(16,32'hffffffff);write_word(0,1);write_word(5,0);
            elapsed=0;r=0;
            while(r[0]!==1 && elapsed<1500) begin read_word(1,r);elapsed=elapsed+1;end
            if(r[0]!==1 || r[1]!==0 || r[2]!==1) $fatal(1,"Busy/error/DONE contract case %0d",c);
            read_word(16,r);if(r!==original_input) $fatal(1,"Busy write corrupted input");
            for(i=0;i<8;i=i+1) begin
                read_word(672+i,r);
                packed_word={vector_mem[p+2344+i*4+3][7:0],vector_mem[p+2344+i*4+2][7:0],
                    vector_mem[p+2344+i*4+1][7:0],vector_mem[p+2344+i*4][7:0]};
                if(r!==packed_word) $fatal(1,"MMIO hidden case %0d word %0d",c,i);
            end
            for(i=0;i<6;i=i+1) begin
                read_word(704+i,r);
                if(r!==vector_mem[p+2376+i]) $fatal(1,"MMIO score case %0d item %0d",c,i);
            end
            read_word(2,r);if(r!==vector_mem[p+2382]) $fatal(1,"MMIO category");
            read_word(3,r);if(r!==39) $fatal(1,"MMIO cycles");
            // Hold one STATUS read across multiple cycles: no read side effect.
            @(negedge clk);ena=1;wea=0;addr=1;
            repeat(5) begin @(posedge clk);#1;if(result[0]!==1) $fatal(1,"STATUS read cleared DONE");end
            @(negedge clk);ena=0;
            read_word(4095,r);if(r!==0) $fatal(1,"Undefined read not zero");
            write_word(0,2);read_word(1,r);if(r!==0) $fatal(1,"ACK did not clear status");
            // Same parameters, second input slot; both stages must really overlap.
            for(i=0;i<16;i=i+1) begin
                packed_word={batch_mem[c*103+i*4+3][7:0],batch_mem[c*103+i*4+2][7:0],
                             batch_mem[c*103+i*4+1][7:0],batch_mem[c*103+i*4][7:0]};
                write_word(768+i,packed_word);read_word(768+i,r);
                if(r!==packed_word) $fatal(1,"Second input readback");
            end
            // Restore configuration after the deliberate busy-write attempt above.
            write_word(5,vector_mem[p+2343]);write_word(6,2);write_word(0,1);
            repeat(20) @(negedge clk);
            // Concurrent CPU weight readback exercises the other synchronous port.
            read_word(64,r);
            packed_word={vector_mem[p+67][7:0],vector_mem[p+66][7:0],vector_mem[p+65][7:0],vector_mem[p+64][7:0]};
            if(r!==packed_word) $fatal(1,"Concurrent weight readback");
            read_word(576,r);
            packed_word={vector_mem[p+2115][7:0],vector_mem[p+2114][7:0],vector_mem[p+2113][7:0],vector_mem[p+2112][7:0]};
            if(r!==packed_word) $fatal(1,"Concurrent FC2 readback");
            write_word(64,32'h12345678);write_word(6,1);
            elapsed=0;r=0;
            while(r[0]!==1 && elapsed<100) begin read_word(1,r);elapsed=elapsed+1;end
            if(r[0]!==1 || r[2]!==1) $fatal(1,"Batch status");
            read_word(6,r);if(r!==2) $fatal(1,"Busy batch config was accepted");
            read_word(64,r);
            packed_word={vector_mem[p+67][7:0],vector_mem[p+66][7:0],vector_mem[p+65][7:0],vector_mem[p+64][7:0]};
            if(r!==packed_word) $fatal(1,"Busy RAM write corrupted model");
            for(i=0;i<8;i=i+1) begin
                read_word(784+i,r);
                packed_word={batch_mem[c*103+64+i*4+3][7:0],batch_mem[c*103+64+i*4+2][7:0],
                             batch_mem[c*103+64+i*4+1][7:0],batch_mem[c*103+64+i*4][7:0]};
                if(r!==packed_word) $fatal(1,"Batch hidden case %0d index %0d",c,i);
            end
            for(i=0;i<6;i=i+1) begin read_word(800+i,r);if(r!==batch_mem[c*103+96+i]) $fatal(1,"Batch score");end
            read_word(806,r);if(r!==batch_mem[c*103+102]) $fatal(1,"Batch category");
            read_word(3,r);if(r!==59) $fatal(1,"Batch cycles");
            read_word(7,r);if(r!==18) $fatal(1,"Batch no overlap");
            read_word(8,r);if(r!==38) $fatal(1,"FC1 cycles");
            read_word(9,r);if(r!==38) $fatal(1,"FC2 cycles");
            write_word(0,2);write_word(6,1);
        end
        // Asynchronous reset while actively computing.
        write_word(0,1);repeat(20) @(negedge clk);rst_ni=0;#1;
        if(dut.busy!==0 || dut.done!==0) $fatal(1,"MMIO reset during operation");
        @(negedge clk);rst_ni=1;read_word(1,r);if(r!==0) $fatal(1,"Reset status");
        read_word(64,r);if(r!==0) $fatal(1,"Reset validity failed to mask old RAM contents");
        read_word(6,r);if(r!==1) $fatal(1,"Reset batch default");
        $display("HAR_MMIO PASS cases=12 packing/readback/busy/invalid-config/held-read/reset/batch/concurrent-memory=PASS");
        $finish;
    end
endmodule
