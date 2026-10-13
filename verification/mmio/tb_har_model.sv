`timescale 1ns/1ps
module tb_har_model;
    logic clk=0,rst_ni=0,ena=0,wea=0;
    logic [11:0] addr=0;
    logic [31:0] data=0;
    wire [31:0] result;
    always #5 clk=~clk;
    simple_npu_top dut(.clka(clk),.rst_ni(rst_ni),.ena(ena),.wea(wea),.addra(addr),.dina(data),.douta(result));
    reg [31:0] weights[0:599],samples[0:4000*105-1];
    string weights_path,samples_path;
    integer count,mode,n,i,slot,row,base,polls,inferences=0,correct=0,pair;
    reg [31:0] r,packed_word;
    task write_word(input integer a,input reg[31:0] d);
        begin @(negedge clk);ena=1;wea=1;addr=a;data=d;
              @(negedge clk);ena=0;wea=0;end
    endtask
    task read_word(input integer a,output reg[31:0] d);
        begin @(negedge clk);ena=1;wea=0;addr=a;
              @(posedge clk);#1;d=result;@(negedge clk);ena=0;end
    endtask
    task load_input(input integer sample_index,input integer destination);
        integer j,p;
        begin
            p=sample_index*105;
            for(j=0;j<16;j=j+1)
                write_word(destination+j,{samples[p+j*4+3][7:0],samples[p+j*4+2][7:0],
                    samples[p+j*4+1][7:0],samples[p+j*4][7:0]});
        end
    endtask
    task check_result(input integer sample_index,input integer output_slot);
        integer j,p;
        reg[31:0] actual,expected;
        begin
            p=sample_index*105;
            for(j=0;j<8;j=j+1) begin
                read_word((output_slot==0 ? 672:784)+j,actual);
                expected={samples[p+64+j*4+3][7:0],samples[p+64+j*4+2][7:0],
                    samples[p+64+j*4+1][7:0],samples[p+64+j*4][7:0]};
                if(actual!==expected) $fatal(1,"Model hidden row=%0d mode=%0d slot=%0d word=%0d",samples[p+104],mode,output_slot,j);
            end
            for(j=0;j<6;j=j+1) begin
                read_word((output_slot==0 ? 704:800)+j,actual);
                if(actual!==samples[p+96+j]) $fatal(1,"Model score row=%0d item=%0d got=%0d expected=%0d",samples[p+104],j,$signed(actual),$signed(samples[p+96+j]));
            end
            read_word(output_slot==0 ? 2:806,actual);
            if(actual!==samples[p+102]) $fatal(1,"Model class differs from integer reference");
            // Accuracy counts compare against true labels separately; an ordinary
            // classifier error must not masquerade as an RTL arithmetic mismatch.
            if(actual==samples[p+103]) correct=correct+1;
            inferences=inferences+1;
        end
    endtask
    initial begin
        if(!$value$plusargs("WEIGHTS=%s",weights_path) || !$value$plusargs("SAMPLES=%s",samples_path) ||
           !$value$plusargs("COUNT=%d",count)) $fatal(1,"Missing model arguments");
        if(count<1 || count>4000) $fatal(1,"Invalid model sample count");
        $readmemh(weights_path,weights);$readmemh(samples_path,samples,0,count*105-1);
        repeat(3) @(negedge clk);rst_ni=1;
        for(i=0;i<560;i=i+1) write_word(64+i,weights[i]);
        for(i=0;i<38;i=i+1) write_word(624+i,weights[560+i]);
        write_word(4,weights[598]);write_word(5,weights[599]);
        // Every real row is evaluated once in single mode and once in paired
        // mode. An odd final row is submitted as a legal single command.
        for(mode=0;mode<2;mode=mode+1) begin
            n=0;
            while(n<count) begin
                pair=mode==1 && n+1<count;
                load_input(n,16);
                if(pair) load_input(n+1,768);
                write_word(6,pair ? 2:1);write_word(0,1);
                polls=0;r=0;
                while(r[0]!==1 && polls<100) begin read_word(1,r);polls=polls+1;end
                if(r!==1) $fatal(1,"Model status/timeout sample=%0d",n);
                check_result(n,0);
                if(pair) check_result(n+1,1);
                read_word(3,r);if(r!==(pair ? 59:39)) $fatal(1,"Model latency");
                read_word(7,r);if(r!==(pair ? 18:0)) $fatal(1,"Model overlap");
                write_word(0,2);
                n=n+(pair ? 2:1);
                if(n%500==0) $display("HAR_MODEL progress mode=%0d rows=%0d/%0d",mode,n,count);
            end
        end
        $display("HAR_MODEL PASS samples=%0d inferences=%0d correct=%0d all_hidden/scores/classes single/batch=PASS",count,inferences,correct);
        $finish;
    end
endmodule
