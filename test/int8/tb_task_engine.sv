`timescale 1ns/1ps
module tb_task_engine;
    reg clk=0,rst_n=0;always #5 clk=~clk;
    reg cpu_req=0,cpu_we=0;
    reg [31:0] cpu_addr=0,cpu_data=0;
    wire [31:0] readback,dma_reg_data;
    wire npu_busy,auto_start,auto_task,dma_busy,dma_done,dma_error,rd_active,wr_active;
    wire [31:0] src,dst,words,araddr,awaddr,wdata;
    wire [3:0] last_be,wstrb;
    wire [7:0] arlen,awlen;
    wire arvalid,arready,rvalid,rready,rlast,awvalid,awready,wvalid,wready,wlast,bvalid,bready;
    wire dma_req,dma_we,dma_conflict;wire [4:0] dma_addr;wire [31:0] dma_wdata;
    reg reading=0,writing=0,response=0;
    reg [1:0] read_phase=0;
    reg [31:0] read_addr=0,write_addr=0,read_data=0;
    integer read_len=0,read_count=0,write_count=0,b_delay=0;
    reg [31:0] rng=32'h12345678;
    reg inject_read_error=0,inject_write_error=0;
    reg last_user=0;
    reg [31:0] mem[0:2047],golden[0:2047];
    wire read_mmio=read_addr[31:28]==7;
    wire [31:0] sink_addr=write_addr+write_count*4;
    wire sink_sram=write_addr[31:28]==8;
    wire read_request=reading && read_mmio && read_phase==0 && !cpu_req && rng[0];
    wire dma_write=wvalid && wready && !sink_sram;
    wire req=cpu_req || dma_write || read_request;
    wire we=cpu_req ? cpu_we:dma_write;
    wire [31:0] address=cpu_req ? cpu_addr:dma_write ? sink_addr:read_addr+read_count*4;
    wire [31:0] data=cpu_req ? cpu_data:wdata;
    assign arready=!reading && rng[0];
    assign rvalid=reading && read_phase==2;
    assign rlast=read_count==read_len;
    assign awready=!writing && !response && rng[2];
    assign wready=writing && rng[3] && (sink_sram || (!cpu_req && !read_request));
    assign bvalid=response && b_delay==0;
    my_npu_subsystem dut(.clk_i(clk),.rst_ni(rst_n),.req_i(req),.we_i(we),
        .addr_i(address),.wdata_i(data),.rdata_o(readback),
        .dma_write_i(dma_write ? 1'b1:cpu_req && cpu_we ? 1'b0:last_user),
        .dma_busy_i(dma_busy),.dma_done_i(dma_done),.dma_error_i(dma_error),
        .dma_read_i(rd_active),.dma_write_active_i(wr_active),
        .auto_start_o(auto_start),.auto_source_o(src),.auto_dest_o(dst),.auto_words_o(words),
        .auto_task_o(auto_task),.auto_last_be_o(last_be),.dma_rdata_i(dma_reg_data),
        .dma_req_o(dma_req),.dma_we_o(dma_we),.dma_addr_o(dma_addr),.dma_wdata_o(dma_wdata),
        .dma_conflict_o(dma_conflict),.npu_busy_o(npu_busy));
    har_dma dma(.clk_i(clk),.rst_ni(rst_n),.reg_req_i(dma_req),.reg_we_i(dma_we),
        .reg_addr_i(dma_addr),.reg_wdata_i(dma_wdata),.reg_rdata_o(dma_reg_data),
        .npu_busy_i(npu_busy),.conflict_i(dma_conflict),
        .auto_start_i(auto_start),.auto_source_i(src),.auto_dest_i(dst),.auto_words_i(words),
        .auto_task_i(auto_task),.auto_last_be_i(last_be),
        .done_o(dma_done),.error_o(dma_error),.read_active_o(rd_active),.write_active_o(wr_active),.busy_o(dma_busy),
        .ar_addr_o(araddr),.ar_len_o(arlen),.ar_valid_o(arvalid),.ar_ready_i(arready),
        .r_data_i(read_data),.r_resp_i(inject_read_error ? 2'b10:2'b00),.r_last_i(rlast),.r_valid_i(rvalid),.r_ready_o(rready),
        .aw_addr_o(awaddr),.aw_len_o(awlen),.aw_valid_o(awvalid),.aw_ready_i(awready),
        .w_data_o(wdata),.w_strb_o(wstrb),.w_last_o(wlast),.w_valid_o(wvalid),.w_ready_i(wready),
        .b_resp_i(inject_write_error && sink_sram ? 2'b10:2'b00),.b_valid_i(bvalid),.b_ready_o(bready));
    integer lane;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n)begin
            reading<=0;writing<=0;response<=0;read_phase<=0;read_count<=0;write_count<=0;
            read_addr<=0;write_addr<=0;read_len<=0;read_data<=0;b_delay<=0;last_user<=0;
        end else begin
            rng<={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
            // Like axi2mem, WUSER can retain DMA ownership during reads/idle.
            if(cpu_req && cpu_we)last_user<=0;else if(dma_write)last_user<=1;
            if(arvalid && arready)begin reading<=1;read_addr<=araddr;read_len<=arlen;read_count<=0;read_phase<=0;end
            if(reading && read_phase==0)begin
                if(read_mmio)begin if(read_request)read_phase<=1;end
                else if(rng[1])begin read_data<=mem[(read_addr-32'h80000000)/4+read_count];read_phase<=2;end
            end
            if(reading && read_phase==1)begin read_data<=readback;read_phase<=2;end
            if(rvalid && rready)begin
                read_phase<=0;
                if(rlast)reading<=0;else read_count<=read_count+1;
            end
            if(awvalid && awready)begin writing<=1;write_addr<=awaddr;write_count<=0;end
            if(wvalid && wready)begin
                if(sink_sram)for(lane=0;lane<4;lane=lane+1)
                    if(wstrb[lane])mem[(sink_addr-32'h80000000)/4][lane*8+:8]<=wdata[lane*8+:8];
                if(wlast)begin writing<=0;response<=1;b_delay<=sink_sram ? 13:3;end
                else write_count<=write_count+1;
            end
            if(response && b_delay>0)b_delay<=b_delay-1;
            if(bvalid && bready)response<=0;
            if(dut.task_valid && dma_busy)$fatal(1,"Published output before final AXI B");
            if(auto_start && dma_busy)$fatal(1,"Overlapping DMA ownership");
            if(dut.task_core_req && dma_write)$fatal(1,"Core port collision");
        end
    end
    task put(input integer byte_addr,input reg [31:0] value);
        begin
            @(negedge clk);cpu_req=1;cpu_we=1;cpu_addr=32'h70000000+byte_addr;cpu_data=value;
            @(negedge clk);cpu_req=0;cpu_we=0;
        end
    endtask
    task check(input integer byte_addr,input reg [31:0] expected);
        begin
            @(negedge clk);cpu_req=1;cpu_we=0;cpu_addr=32'h70000000+byte_addr;
            @(posedge clk);#1;
            if(readback!==expected)$fatal(1,"MMIO %h expected %h got %h state=%d err=%d",byte_addr,expected,readback,dut.tasks.state,dut.tasks.error_q);
            @(negedge clk);cpu_req=0;
        end
    endtask
    task await_done;
        integer t;
        begin
            t=0;
            while(dut.task_busy && t<200000)begin @(negedge clk);t=t+1;end
            if(t>=200000)$fatal(1,"Task timeout state=%d core=%d dma=%d",dut.tasks.state,dut.i_npu_core.core.state,dma.state);
        end
    endtask
    task run_case(input string image,expected,input integer count,code,protect);
        integer i;
        begin
            $readmemh(image,mem);$readmemh(expected,golden);
            put('h1600,2);put('h1608,'h80001800);put('h160c,count);put('h1600,1);
            if(protect)begin
                put('h1608,'h80000000);put('h160c,99);put('h1600,1);put('h1600,2);
                put('h80,1);put('hd08,'h80000000);put('h1640,'hffffffff);
            end
            await_done();
            check('h1604,code==0 ? (protect ? 25:9):(protect ? 21:5));check('h1618,code);
            check('h1608,'h80001800);check('h160c,count);
            if(protect)check('h1624,1);
            if(code==0)begin
                check('h1620,count);
                for(i=0;i<2048;i=i+1)
                    if(mem[i]!==golden[i])$fatal(1,"Task SRAM %h got %h expected %h",i*4,mem[i],golden[i]);
            end
            $display("TASK_CASE PASS image=%s tasks=%0d error=%0d cycles=%0d",image,count,code,dut.tasks.cycles_q);
        end
    endtask
    task reset_case(input integer target_state);
        integer t;
        begin
            $readmemh("fc_64_32_4_input.hex",mem);
            put('h1600,2);put('h1608,'h80001800);put('h160c,1);put('h1600,1);t=0;
            while(dut.tasks.state!=target_state && t<20000)begin @(negedge clk);t=t+1;end
            if(t>=20000)$fatal(1,"Reset test could not reach state %0d",target_state);
            rst_n=0;repeat(3) @(negedge clk);rst_n=1;
            repeat(15) @(negedge clk);
            check('h1604,0);check('h1620,0);check('h1608,0);
            if(dma_busy || npu_busy || dut.i_npu_core.partial_valid || dut.tasks.forward_q)
                $fatal(1,"Reset retained active context");
            run_case("fc_1_1_1_input.hex","fc_1_1_1_golden.hex",1,0,0);
            $display("TASK_RESET PASS state=%0d",target_state);
        end
    endtask
    // Generated test cases are appended by run_task_engine.py.
