`timescale 1ns/1ps
module tb_raw_gemv;
    reg clk=0,rst_n=0;
    always #5 clk=~clk;
    reg cpu_req=0,cpu_we=0;
    reg [11:0] cpu_addr=0;
    reg [31:0] cpu_data=0;
    wire [31:0] readback;
    wire npu_busy,auto_start,dma_busy,dma_done,dma_error,rd_active,wr_active;
    wire [31:0] src,dst,words,araddr,awaddr,rdata,wdata;
    wire [7:0] arlen,awlen;
    wire arvalid,arready,rvalid,rready,rlast,awvalid,awready,wvalid,wready,wlast,bvalid,bready;
    reg reading=0,writing=0,response=0;
    reg [31:0] read_addr,write_addr;
    integer read_len,read_count,write_count;
    reg [31:0] rng=32'h12345678;
    reg inject_error=0,inject_write_error=0,inject_w2_error=0,early_last=0,late_last=0;
    reg previous_layer=0;
    reg raw_monitor=0;
    integer descriptors=0;
    reg [31:0] mem[0:2047];
    wire dma_write=wvalid && wready;
    wire [31:0] sink_addr=write_addr+write_count*4;
    assign arready=!reading && rng[0];
    assign rvalid=reading && rng[1];
    assign rdata=mem[(read_addr-32'h80000000)/4+read_count];
    assign rlast=early_last ? read_count==1 : late_last ? read_count==read_len+1 : read_count==read_len;
    assign awready=!writing && !response && rng[2];
    assign wready=writing && rng[3] && !cpu_req;
    assign bvalid=response && rng[4];
    simple_npu_top dut(.clka(clk),.rst_ni(rst_n),.ena(cpu_req || dma_write),
        .wea(dma_write || cpu_we),.dma_write_i(dma_write),
        .addra(dma_write ? sink_addr[13:2]:cpu_addr),.dina(dma_write ? wdata:cpu_data),
        .douta(readback),.busy_o(npu_busy),.auto_start_o(auto_start),
        .auto_source_o(src),.auto_dest_o(dst),.auto_words_o(words),
        .dma_busy_i(dma_busy),.dma_done_i(dma_done),.dma_error_i(dma_error),
        .dma_read_i(rd_active),.dma_write_active_i(wr_active));
    har_dma dma(.clk_i(clk),.rst_ni(rst_n),.reg_req_i(1'b0),.reg_we_i(1'b0),
        .reg_addr_i(5'd0),.reg_wdata_i(32'd0),.reg_rdata_o(),.npu_busy_i(npu_busy),.conflict_i(1'b0),
        .auto_start_i(auto_start),.auto_source_i(src),.auto_dest_i(dst),.auto_words_i(words),
        .done_o(dma_done),.error_o(dma_error),.read_active_o(rd_active),.write_active_o(wr_active),.busy_o(dma_busy),
        .ar_addr_o(araddr),.ar_len_o(arlen),.ar_valid_o(arvalid),.ar_ready_i(arready),
        .r_data_i(rdata),.r_resp_i((inject_error || (inject_w2_error && dut.pending_w2)) ? 2'b10:2'b00),
        .r_last_i(rlast),.r_valid_i(rvalid),.r_ready_o(rready),
        .aw_addr_o(awaddr),.aw_len_o(awlen),.aw_valid_o(awvalid),.aw_ready_i(awready),
        .w_data_o(wdata),.w_last_o(wlast),.w_valid_o(wvalid),.w_ready_i(wready),
        .b_resp_i(inject_write_error ? 2'b10:2'b00),.b_valid_i(bvalid),.b_ready_o(bready));
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin reading<=0;writing<=0;response<=0;read_count<=0;write_count<=0;read_addr<=0;write_addr<=0;read_len<=0;end
        else begin
            rng<={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
            if(arvalid && arready) begin reading<=1;read_addr<=araddr;read_len<=arlen;read_count<=0;end
            if(rvalid && rready) begin if(rlast) reading<=0;else read_count<=read_count+1;end
            if(awvalid && awready) begin writing<=1;write_addr<=awaddr;write_count<=0;end
            if(dma_write) begin
                if(wlast) begin writing<=0;response<=1;end
                else write_count<=write_count+1;
            end
            if(bvalid && bready) response<=0;
            if(dma_write &&
               (dut.ready_w1[sink_addr[6]] || dut.ready_w2[sink_addr[6]]))
                $fatal(1,"Overwrote a published tile");
            if(npu_busy && dut.layer && !previous_layer && !raw_monitor && dut.next_w2==0)
                $fatal(1,"FC2 started without an earlier W2 prefetch");
            previous_layer<=npu_busy ? dut.layer:1'b0;
            if(raw_monitor && auto_start) begin
                if(src!==mem['h1f04/4]+descriptors*64 || words!==32'd16)
                    $fatal(1,"RAW_GEMV_FAIL unexpected descriptor src=%h words=%d index=%d",src,words,descriptors);
                descriptors<=descriptors+1;
            end
            if(raw_monitor && npu_busy && dut.layer)
                $fatal(1,"RAW_GEMV_FAIL entered FC2");
            if(dut.consumed && dut.core.product_sample!=dut.core.batch_q-1'b1)
                $fatal(1,"Tile released before all samples");
        end
    end
    task put(input integer byte_addr,input reg [31:0] value);
        begin
            @(negedge clk);cpu_req=1;cpu_we=1;cpu_addr=byte_addr/4;cpu_data=value;
            @(negedge clk);cpu_req=0;cpu_we=0;
        end
    endtask
    task check(input integer byte_addr,input reg [31:0] expected);
        begin
            @(negedge clk);cpu_req=1;cpu_we=0;cpu_addr=byte_addr/4;
            @(posedge clk);#1;
            if(readback!==expected) $fatal(1,"MMIO %h expected %h actual %h",byte_addr,expected,readback);
            @(negedge clk);cpu_req=0;
        end
    endtask
    task get(input integer byte_addr,output reg [31:0] value);
        begin
            @(negedge clk);cpu_req=1;cpu_we=0;cpu_addr=byte_addr/4;
            @(posedge clk);#1;value=readback;
            @(negedge clk);cpu_req=0;
        end
    endtask
    task await_done;
        integer timeout;
        begin
            timeout=0;
            while(!dut.done && timeout<30000) begin @(negedge clk);timeout=timeout+1;end
            if(timeout>=30000) $fatal(1,"RAW_GEMV_FAIL timeout");
        end
    endtask
    task configure_raw;
        integer n,j,address,batch;
        begin
            put(0,2);check(4,0);
            put('h3c,1);
            batch=mem['h1f00/4];
            put('h18,batch);put('h20,mem['h1f04/4]);
            // This pointer must never be inspected or fetched in RAW mode.
            put('h24,32'hffffffff);
            put('h10,65535);put('h14,31);
            for(n=0;n<batch;n=n+1) begin
                address=n==0 ? 'h40 : n==1 ? 'hc00 : 'h1000+(n-2)*'h40;
                for(j=0;j<16;j=j+1) put(address+j*4,mem['h1800/4+n*16+j]);
            end
            for(j=0;j<32;j=j+1) put('h9c0+j*4,mem['h1900/4+j]);
            check('h3c,1);check('h88,0);check('h84,0);check(4,0);
        end
    endtask
    task launch_raw;
        begin
            raw_monitor=1;descriptors=0;
            put(0,1);
        end
    endtask
    task select_result(input integer index,input reg [31:0] expected);
        reg [31:0] ready;
        integer timeout;
        begin
            put('h80,index);
            ready=0;timeout=0;
            while(ready==0 && timeout<16) begin
                get('h88,ready);timeout=timeout+1;
            end
            if(ready!==1) $fatal(1,"RAW_GEMV_FAIL result ready index=%d value=%h",index,ready);
            check('h84,expected);
            // Reading DATA does not consume the result.
            check('h88,1);check('h84,expected);
        end
    endtask
    task verify_raw;
        integer n,j,output_index,batch;
        begin
            await_done();raw_monitor=0;
            batch=mem['h1f00/4];
            check(4,1);check('h30,32);check('h28,batch*128);check('h2c,0);
            if(descriptors!=32 || dut.next_w2!=0)
                $fatal(1,"RAW_GEMV_FAIL W2 fetched descriptors=%d next_w2=%d",descriptors,dut.next_w2);
            check('h88,0);check('h84,0);
            // Configuration may change while idle. Result bounds must still
            // describe the batch latched by its own START, not this new value.
            put('h18,batch==1 ? 4:1);
            for(n=0;n<batch;n=n+1)
                for(j=0;j<32;j=j+1) begin
                    output_index=(13*j+31)%32;
                    select_result(n*32+output_index,mem['h1a00/4+n*32+output_index]);
                end
            for(n=0;n<batch;n=n+1) begin
                // No requantized outputs are produced by RAW execution.
                for(j=0;j<8;j=j+1)
                    check((n==0 ? 'ha80 : n==1 ? 'hc40 : 'h1200+(n-2)*'h40)+j*4,0);
            end
            // Reading while MODE=0 is quiet. Switching back without START
            // restores the existing RAW result and its selection.
            put('h3c,0);check('h88,0);check('h84,0);
            put('h3c,1);check('h88,1);
            select_result((batch-1)*32+31,mem['h1a00/4+(batch-1)*32+31]);
            put('h80,batch<4 ? batch*32:128);check(4,5);
            check('h88,0);check('h84,0);
            put(0,2);check(4,0);check('h88,0);check('h84,0);
            // ACK invalidates read permission, even though the arrays retain data.
            put('h80,0);check(4,4);check('h88,0);check('h84,0);
            put(0,2);check(4,0);
        end
    endtask
    task configure_legacy;
        integer n,j,address,batch;
        begin
            put(0,2);put('h3c,0);
            batch=mem['h1f08/4];
            put('h20,mem['h1f0c/4]);put('h24,'h80001800);
            put('h10,mem['h1f00/4]);put('h14,mem['h1f04/4]);put('h18,batch);
            for(n=0;n<batch;n=n+1) begin
                address=n==0 ? 'h40 : n==1 ? 'hc00 : 'h1000+(n-2)*'h40;
                for(j=0;j<16;j=j+1) put(address+j*4,mem['h1a00/4+n*16+j]);
            end
            for(j=0;j<32;j=j+1) put('h9c0+j*4,mem['h1900/4+j]);
            for(j=0;j<6;j=j+1) put('ha40+j*4,mem['h1980/4+j]);
        end
    endtask
    task verify_legacy;
        integer n,j,hidden,scores,category,batch;
        begin
            put(0,1);await_done();check(4,1);check('h30,64);
            batch=mem['h1f08/4];
            check('h28,batch*128);check('h2c,batch*16);
            for(n=0;n<batch;n=n+1) begin
                hidden=n==0 ? 'ha80 : n==1 ? 'hc40 : 'h1200+(n-2)*'h40;
                scores=n==0 ? 'hb00 : n==1 ? 'hc80 : hidden+'h20;
                category=n==0 ? 8 : n==1 ? 'hc98 : hidden+'h38;
                for(j=0;j<8;j=j+1) check(hidden+j*4,mem['h1c00/4+n*16+j]);
                for(j=0;j<6;j=j+1) check(scores+j*4,mem['h1c20/4+n*16+j]);
                check(category,mem['h1c38/4+n*16]);
            end
            check('h88,0);check('h84,0);
            put('h3c,1);put('h80,0);check(4,5);
            check('h88,0);check('h84,0);put(0,2);
            $display("RAW_LEGACY_SWITCH PASS hidden_scores_class");
        end
    endtask
    task pulse_reset;
        begin
            raw_monitor=0;rst_n=0;
            repeat(3) @(negedge clk);rst_n=1;
            check('h3c,0);check(4,0);check('h88,0);check('h84,0);
        end
    endtask
    task invalidate_inflight_selection(input reg restart);
        integer n;
        reg [21:0] next_value;
        begin
            configure_raw();launch_raw();await_done();raw_monitor=0;
            select_result(31,mem['h1a00/4+31]);
            // The next command has a different output 0, so a stale selected
            // value cannot accidentally satisfy its final numerical check.
            if(restart) put('h9c0,mem['h1900/4]+1);
            // Consecutive positive-edge commands: no idle write cycle is
            // inserted between RAW_INDEX and ACK/new START.
            @(negedge clk);cpu_req=1;cpu_we=1;cpu_addr='h80/4;cpu_data=0;
            @(negedge clk);
            if(restart) begin raw_monitor=1;descriptors=0;end
            cpu_addr=0;cpu_data=restart ? 1:2;
            @(negedge clk);cpu_req=0;cpu_we=0;
            check(4,restart ? 2:0);
            for(n=0;n<4;n=n+1) begin check('h88,0);check('h84,0);end
            if(restart) begin
                await_done();raw_monitor=0;
                check(4,1);check('h88,0);check('h84,0);
                if(descriptors!=32) $fatal(1,"RAW_GEMV_FAIL restarted descriptor count");
                next_value=mem['h1a00/4]+1;
                select_result(0,{{10{next_value[21]}},next_value});
            end
            put(0,2);check(4,0);check('h88,0);check('h84,0);
            $display("RAW_PIPELINE_INVALIDATION PASS restart=%d",restart);
        end
    endtask
    string directory,filename;
    integer count,which,fault;
    initial begin
        if(!$value$plusargs("DIR=%s",directory)) $fatal(1,"DIR required");
        if(!$value$plusargs("COUNT=%d",count) || count<1) $fatal(1,"Positive COUNT required");
        if($bits(dut.core.a1[0][0])!=22 || $bits(dut.core.a2[0][0])!=22 ||
           $bits(dut.b1[0])!=22 || $bits(dut.b2[0])!=22 ||
           $size(dut.core.a1,1)!=4 || $size(dut.core.a1,2)!=32 ||
           $size(dut.core.a2,1)!=4 || $size(dut.core.a2,2)!=6)
            $fatal(1,"RAW_GEMV_FAIL INT22 accumulator geometry changed");
        #1;pulse_reset();
        put('h3c,2);check(4,4);check('h3c,0);put(0,2);
        put('h3c,1);put('h3c,32'hffffffff);check(4,4);check('h3c,1);put(0,2);
        put('h80,0);check(4,4);check('h88,0);check('h84,0);put(0,2);
        for(which=0;which<count;which=which+1) begin
            filename=$sformatf("%s/case_%0d.hex",directory,which);$readmemh(filename,mem);
            configure_raw();launch_raw();verify_raw();
            $display("RAW_CASE PASS case=%d batch=%d",which,mem['h1f00/4]);
        end
        // Busy writes must not alter the active command or clear its mode.
        configure_raw();launch_raw();repeat(12) @(negedge clk);
        put('h3c,0);put('h18,1);put('h80,0);put(0,1);
        await_done();raw_monitor=0;
        check('h3c,1);check('h18,mem['h1f00/4]);check(4,5);check('h88,0);check('h84,0);
        if(descriptors!=32) $fatal(1,"RAW_GEMV_FAIL busy START restarted command");
        put(0,2);
        for(fault=0;fault<4;fault=fault+1) begin
            configure_raw();
            inject_error=fault==0;inject_write_error=fault==1;
            early_last=fault==2;late_last=fault==3;
            launch_raw();await_done();raw_monitor=0;
            check(4,5);check('h88,0);check('h84,0);
            put('h80,0);check(4,5);check('h88,0);check('h84,0);
            if(dut.bank_published!==0) $fatal(1,"RAW_GEMV_FAIL failed tile published");
            inject_error=0;inject_write_error=0;early_last=0;late_last=0;
            put(0,2);check(4,0);
            $display("RAW_DMA_FAULT PASS kind=%d",fault);
        end
        configure_raw();launch_raw();repeat(12) @(negedge clk);pulse_reset();
        if(npu_busy || dma_busy || dut.bank_published!==0)
            $fatal(1,"RAW_GEMV_FAIL reset retained operation");
        configure_raw();launch_raw();verify_raw();
        invalidate_inflight_selection(0);
        invalidate_inflight_selection(1);
        filename=$sformatf("%s/legacy.hex",directory);$readmemh(filename,mem);
        configure_legacy();verify_legacy();
        filename=$sformatf("%s/case_0.hex",directory);$readmemh(filename,mem);
        configure_raw();launch_raw();verify_raw();
        $display("RAW_GEMV_PASS cases=%0d",count);$finish;
    end
endmodule
