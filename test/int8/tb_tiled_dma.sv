`timescale 1ns/1ps
module tb_tiled_dma;
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
            if(npu_busy && dut.layer && !previous_layer && dut.next_w2==0)
                $fatal(1,"FC2 started without an earlier W2 prefetch");
            previous_layer<=npu_busy ? dut.layer:1'b0;
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
    task configure;
        integer n,input_addr,output_addr,golden_addr,class_addr,batch;
        begin
            batch=mem['h1f08/4];
            put('h20,mem['h1f0c/4]);put('h24,'h80001800);
            put('h10,mem['h1f00/4]);put('h14,mem['h1f04/4]);put('h18,batch);
            for(n=0;n<batch;n=n+1) begin
                input_addr=n==0 ? 'h40 : n==1 ? 'hc00 : 'h1000+(n-2)*'h40;
                for(j=0;j<16;j=j+1) put(input_addr+j*4,mem['h1a00/4+n*16+j]);
            end
            for(j=0;j<32;j=j+1) put('h9c0+j*4,mem['h1900/4+j]);
            for(j=0;j<6;j=j+1) put('ha40+j*4,mem['h1980/4+j]);
        end
    endtask
    task await_done;
        integer timeout;
        begin
            timeout=0;
            while(!dut.done && timeout<30000) begin @(negedge clk);timeout=timeout+1;end
            if(timeout>=30000) $fatal(1,"DMA/NPU timeout");
        end
    endtask
    string directory,filename;
    integer count,which,j,n,batch,input_addr,output_addr,golden_addr,class_addr;
    initial begin
        if(!$value$plusargs("DIR=%s",directory)) $fatal(1,"DIR required");
        if(!$value$plusargs("COUNT=%d",count)) count=24;
        #1;rst_n=0;repeat(3) @(negedge clk);rst_n=1;
        // Invalid SRAM pointer cannot start an inference.
        put(0,1);check(4,4);
        for(which=0;which<count;which=which+1) begin
            filename=$sformatf("%s/case_%0d.hex",directory,which);$readmemh(filename,mem);
            configure();put(0,1);await_done();check(4,1);check('h30,64);
            batch=mem['h1f08/4];
            if(batch>1 && (dut.read_overlap==0 || dut.write_overlap==0))
                $fatal(1,"No real DMA read/write and MAC overlap");
            for(n=0;n<batch;n=n+1) begin
                output_addr=n==0 ? 'ha80 : n==1 ? 'hc40 : 'h1200+(n-2)*'h40;
                golden_addr='h1c00+n*'h40;
                input_addr=n==0 ? 'hb00 : n==1 ? 'hc80 : output_addr+'h20;
                class_addr=n==0 ? 8 : n==1 ? 'hc98 : output_addr+'h38;
                for(j=0;j<8;j=j+1) check(output_addr+j*4,mem[golden_addr/4+j]);
                for(j=0;j<6;j=j+1) check(input_addr+j*4,mem[golden_addr/4+8+j]);
                check(class_addr,mem[golden_addr/4+14]);
            end
            check('h28,batch*32);check('h2c,batch*32);
            $display("CASE %0d PASS cycles=%0d fc1=%0d fc2=%0d read_overlap=%0d write_overlap=%0d",
                which,dut.cycles,dut.fc1_cycles,dut.fc2_cycles,dut.read_overlap,dut.write_overlap);
            put(0,2);
        end
        // A failed SRAM read must never publish a partial tile or compute it.
        $display("ERROR_TEST read");configure();inject_error=1;put(0,1);await_done();check(4,5);
        if(dut.bank_published!==0) $fatal(1,"Failed DMA tile was published");
        inject_error=0;put(0,2);configure();put(0,1);await_done();check(4,1);
        $display("ERROR_TEST write");put(0,2);inject_write_error=1;put(0,1);await_done();check(4,5);
        if(dut.bank_published!==0) $fatal(1,"Failed DMA write was published");
        inject_write_error=0;put(0,2);
        $display("ERROR_TEST early");early_last=1;put(0,1);await_done();check(4,5);early_last=0;put(0,2);
        $display("ERROR_TEST late");late_last=1;put(0,1);await_done();check(4,5);late_last=0;put(0,2);
        $display("ERROR_TEST W2 prefetch");configure();inject_w2_error=1;put(0,1);await_done();check(4,5);
        if(dut.next_w2==0) $fatal(1,"W2 failure was not observed in a W2 prefetch");
        inject_w2_error=0;put(0,2);
        // Busy configuration and CPU tile writes are rejected, preserving results.
        $display("ERROR_TEST busy write");configure();put(0,1);repeat(12) @(negedge clk);put('h10,32'h12345678);put('h100,32'hffffffff);
        await_done();check(4,5);check('h10,mem['h1f00/4]);
        for(j=0;j<6;j=j+1) check('hb00+j*4,mem['h1c20/4+j]);put(0,2);
        // Reset during an outstanding transfer discards all publication state.
        put(0,2);put(0,1);repeat(12) @(negedge clk);rst_n=0;repeat(3) @(negedge clk);rst_n=1;
        if(dut.bank_published!==0 || npu_busy!==0) $fatal(1,"Reset retained DMA/compute work");
        configure();put(0,1);await_done();check(4,1);
        $display("INT8_TILED_DMA PASS cases=%0d",count);$finish;
    end
endmodule
