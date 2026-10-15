`timescale 1ns/1ps
module tb_dma_ingress;
    reg clk=0,rst_n=0,req=0,we=0,tag=0,dma_busy=0;
    always #5 clk=~clk;
    reg [31:0] addr=0,data=0;
    wire [31:0] result,ctrl_data;
    wire ctrl_req,ctrl_we,conflict,npu_busy;
    wire [4:0] ctrl_addr;
    my_npu_subsystem dut(.clk_i(clk),.rst_ni(rst_n),.req_i(req),.we_i(we),
        .addr_i(addr),.wdata_i(data),.rdata_o(result),
        .dma_write_i(tag),.dma_busy_i(dma_busy),.dma_rdata_i(32'h12345678),
        .dma_req_o(ctrl_req),.dma_we_o(ctrl_we),.dma_addr_o(ctrl_addr),
        .dma_wdata_o(ctrl_data),.dma_conflict_o(conflict),.npu_busy_o(npu_busy));
    task automatic put(input [31:0] a,d,input bit dma,input bit blocked);
        @(negedge clk);req=1;we=1;addr=a;data=d;tag=dma;#1;
        if(conflict!==blocked) $fatal(1,"DMA ingress conflict mismatch");
        @(posedge clk);#1;@(negedge clk);req=0;we=0;tag=0;
    endtask
    task automatic get(input [31:0] a,input [31:0] expected);
        @(negedge clk);req=1;we=0;addr=a;
        @(posedge clk);#1;if(result!==expected) $fatal(1,"DMA ingress read mismatch got=%h",result);
        @(negedge clk);req=0;
    endtask
    initial begin
        repeat(3) @(negedge clk);rst_n=1;
        put(32'h70000040,32'h11223344,0,0);get(32'h70000040,32'h11223344);
        dma_busy=1;
        put(32'h70000040,32'hffffffff,0,1);get(32'h70000040,32'h11223344);
        put(32'h70000000,1,0,1);if(npu_busy) $fatal(1,"CPU started NPU during DMA");
        put(32'h70000040,32'habcdef12,1,0);get(32'h70000040,32'habcdef12);
        get(32'h70000d08,32'h12345678);
        dma_busy=0;
        put(32'h70000000,1,0,0);if(!npu_busy) $fatal(1,"NPU start blocked after DMA");
        repeat(42) @(negedge clk);if(npu_busy) $fatal(1,"NPU did not finish");
        $display("DMA_INGRESS PASS host_guard=1 tagged_dma=1 csr_read=1");$finish;
    end
endmodule
