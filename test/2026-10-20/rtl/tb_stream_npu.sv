`timescale 1ns/1ps
module tb_stream_npu;
    reg clk=0,rst=0,ena=0,we=0;
    reg [11:0] addr=0;
    reg [31:0] data=0;
    reg commit=0,abort_packet=0;
    wire [31:0] dout;
    wire busy,ready;
    always #5 clk=~clk;
    har_stream_top dut(.clka(clk),.rst_ni(rst),.ena(ena),.wea(we),.addra(addr),.dina(data),
        .stream_commit_i(commit),.stream_abort_i(abort_packet),.stream_commit_count_i(2'd1),
        .douta(dout),.busy_o(busy),.stream_ready_o(ready));
    reg [31:0] params[0:599];
    reg [31:0] vectors[0:138508];
    reg [8191:0] param_path,vector_path;
    integer n,j,check_j,mode,received,clock_count,previous,first_cycle;
    integer samples,batch_base,batch_size,total_cycles,total_span;
    task write_word;
        input integer a;
        input [31:0] d;
        begin @(negedge clk);ena=1;we=1;addr=a;data=d;@(posedge clk);#1;end
    endtask
    task idle;
        begin @(negedge clk);ena=0;we=0;end
    endtask
    always @(posedge clk) begin
        clock_count=clock_count+1;
        #2;
        if(rst && dut.result_valid) begin
            if(dut.result_id!=received) $fatal(1,"Frame order");
            for(check_j=0;check_j<32;check_j=check_j+1)
                if(dut.result_hidden[check_j*8+:8]!==vectors[(batch_base+received)*47+8+check_j][7:0])
                    $fatal(1,"Hidden mismatch frame=%0d row=%0d",received,check_j);
            for(check_j=0;check_j<6;check_j=check_j+1)
                if(dut.result_scores[check_j*32+:32]!==vectors[(batch_base+received)*47+40+check_j])
                    $fatal(1,"Score mismatch frame=%0d row=%0d",received,check_j);
            if(dut.result_class!==vectors[(batch_base+received)*47+46][2:0]) $fatal(1,"Class mismatch");
            if(received==0) first_cycle=clock_count;
            if(received>0 && mode!=0 && clock_count-previous!=(mode==3 ? 16:20))
                $fatal(1,"Bad interval mode=%0d frame=%0d II=%0d",mode,received,clock_count-previous);
            previous=clock_count;received=received+1;
        end
    end
    initial begin
        clock_count=0;received=0;previous=0;mode=0;first_cycle=0;batch_base=0;
        samples=24;
        if($value$plusargs("COUNT=%d",samples)) begin end
        if(samples<1 || samples>2947) $fatal(1,"COUNT range");
        if(!$value$plusargs("PARAMS=%s",param_path)) $fatal(1,"PARAMS");
        if(!$value$plusargs("VECTORS=%s",vector_path)) $fatal(1,"VECTORS");
        $readmemh(param_path,params);$readmemh(vector_path,vectors,0,samples*47-1);
        repeat(3) @(negedge clk);rst=1;
        for(n=0;n<598;n=n+1) write_word(64+n,params[n]);
        write_word(4,params[598]);write_word(5,params[599]);idle;
        begin
            mode=3;total_cycles=0;total_span=0;
            batch_base=0;
            while(batch_base<samples) begin
                batch_size=samples-batch_base>64 ? 64:samples-batch_base;
                received=0;previous=0;
                write_word(962,batch_size);write_word(963,mode);write_word(960,1);idle;
                for(n=0;n<batch_size;n=n+1) begin
                    wait(ready);
                    for(j=0;j<8;j=j+1) write_word(896+j,vectors[(batch_base+n)*47+j]);
                    idle;commit=1;@(posedge clk);#1;@(negedge clk);commit=0;
                end
                wait(!busy);repeat(2) @(negedge clk);
                if(received!=batch_size || dut.error || dut.fc1_issues!=batch_size*16 || dut.fc2_issues!=batch_size*16)
                    $fatal(1,"Accounting/error mode=%0d frames=%0d issues=%0d/%0d",mode,received,dut.fc1_issues,dut.fc2_issues);
                total_cycles=total_cycles+dut.cycles;total_span=total_span+previous-first_cycle;
                batch_base=batch_base+batch_size;
            end
            $display("STREAM_UNIT mode=%0d samples=%0d cycles=%0d result_span=%0d",mode,samples,total_cycles,total_span);
        end
        write_word(963,0);idle;
        if(!dut.error) $fatal(1,"Retired pipeline configuration accepted");
        write_word(963,3);idle;
        // Partial/failed packets must not be submitted to the arithmetic core.
        write_word(962,1);write_word(963,3);write_word(960,1);idle;
        for(j=0;j<8;j=j+1) write_word(896+j,vectors[j]);
        idle;abort_packet=1;@(posedge clk);#1;@(negedge clk);abort_packet=0;
        if(dut.accepted!=0 || !dut.error || dut.pending_count!=0) $fatal(1,"Abort committed a packet");
        rst=0;repeat(3) @(negedge clk);rst=1;
        write_word(962,1);write_word(960,1);write_word(897,1);idle;
        if(!dut.error || dut.accepted!=0) $fatal(1,"Out-of-order packet accepted");
        rst=0;repeat(3) @(negedge clk);rst=1;
        write_word(962,1);write_word(960,1);idle;
        for(j=0;j<8;j=j+1) write_word(896+j,vectors[j]);
        idle;commit=1;@(posedge clk);#1;@(negedge clk);commit=0;
        wait(dut.w1_re);repeat(5) @(negedge clk);rst=0;
        repeat(3) @(negedge clk);rst=1;
        repeat(25) begin @(negedge clk);if(busy || dut.result_valid || dut.accepted!=0 || dut.retired!=0) $fatal(1,"Reset recovery");end
        $display("STREAM_NPU PASS exact hidden/score/class exact frame checks, abort/order/reset checks");$finish;
    end
    initial begin #1000000;$display("DEBUG mode=%0d n=%0d received=%0d err=%0d idx=%0d ready=%0d accepted=%0d retired=%0d xv=%b hv=%b occ=%b s1=%0d c1=%0d s2=%0d c2=%0d",mode,n,received,dut.error,dut.packet_index,ready,dut.accepted,dut.retired,dut.core.xv,dut.core.hv,dut.core.occupied,dut.core.s1_run,dut.core.c1,dut.core.s2_run,dut.core.c2);$fatal(1,"Timeout");end
endmodule
