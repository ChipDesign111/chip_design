`timescale 1ns/1ps
// SRAM simulation loader and passive CPU-write completion monitor.
module tb_soc #(
    parameter INIT_FILE = "", GOLD_FILE = ""
);
    reg clk_i = 0, rst_ni = 0;
    wire td_o;
    always #5 clk_i = ~clk_i;
    my_soc_top dut (.clk_i(clk_i), .rst_ni(rst_ni),
        .tck_i(1'b0), .tms_i(1'b0), .td_i(1'b0), .td_o(td_o));
    reg [31:0] image [0:2047];
    reg load_req = 0;
    reg [31:0] load_addr = 0, load_data = 0;
    reg [31:0] magic_status = 0;
    reg [31:0] parameter_cycles=0,input_cycles=0,application_cycles=0,dma_engine_cycles=0;
    reg [31:0] warm_cycles=0;
    reg [31:0] dma_read_beats=0,dma_write_beats=0,dma_read_bursts=0,dma_write_bursts=0;
    integer cycle_count = 0;
    reg [31:0] gold[0:935];
    integer result_count=0;
    reg [31:0] compute_cycles=0,transfer_compute_cycles=0;
    task check_frame;
        input [255:0] hidden;
        input [191:0] scores;
        input [2:0] class_id;
        integer j;
        begin
            if(result_count>=24) $fatal(1,"Extra result");
            for(j=0;j<32;j=j+1)
                if(hidden[j*8+:8]!==gold[result_count*39+j][7:0])
                    $fatal(1,"Hidden mismatch sample=%0d neuron=%0d",result_count,j);
            for(j=0;j<6;j=j+1)
                if(scores[j*32+:32]!==gold[result_count*39+32+j])
                    $fatal(1,"Score mismatch sample=%0d neuron=%0d",result_count,j);
            if(class_id!==gold[result_count*39+38][2:0]) $fatal(1,"Class mismatch");
            result_count=result_count+1;
        end
    endtask
    initial begin
        if(GOLD_FILE=="") $fatal(1,"Missing gold");
        $readmemh(GOLD_FILE,gold);
    end
    always @(posedge clk_i) if(rst_ni) begin
        if(dut.i_npu_subsystem.i_npu_core.result_valid)
            check_frame(dut.i_npu_subsystem.i_npu_core.result_hidden,
                        dut.i_npu_subsystem.i_npu_core.result_scores,
                        dut.i_npu_subsystem.i_npu_core.result_class);
        if(dut.i_npu_subsystem.i_npu_core.w1_re || dut.i_npu_subsystem.i_npu_core.w2_re) begin
            compute_cycles<=compute_cycles+1;
            if((dut.slave[3].r_valid && dut.slave[3].r_ready) || (dut.slave[3].w_valid && dut.slave[3].w_ready))
                transfer_compute_cycles<=transfer_compute_cycles+1;
        end
    end

    // Observe real CPU/AXI writes; never inject a completion status.
    always @(posedge clk_i) begin
        if(rst_ni) begin
            if(dut.slave[3].ar_valid && dut.slave[3].ar_ready) dma_read_bursts<=dma_read_bursts+1;
            if(dut.slave[3].aw_valid && dut.slave[3].aw_ready) dma_write_bursts<=dma_write_bursts+1;
            if(dut.slave[3].r_valid && dut.slave[3].r_ready) dma_read_beats<=dma_read_beats+1;
            if(dut.slave[3].w_valid && dut.slave[3].w_ready) dma_write_beats<=dma_write_beats+1;
        end
        if (rst_ni && dut.sram_req && dut.sram_we && dut.sram_be==4'hf) begin
            case(dut.sram_addr)
                32'h80001fc0:parameter_cycles<=dut.sram_wdata;
                32'h80001fc4:input_cycles<=dut.sram_wdata;
                32'h80001fc8:application_cycles<=dut.sram_wdata;
                32'h80001fcc:dma_engine_cycles<=dut.sram_wdata;
                32'h80001fd0:warm_cycles<=dut.sram_wdata;
                default:begin end
            endcase
        end
        if (rst_ni && dut.sram_req && dut.sram_we &&
            dut.sram_addr == 32'h80001fe0)
            for (integer b = 0; b < 4; b = b + 1)
                if (dut.sram_be[b])
                    magic_status[b*8 +: 8] <= dut.sram_wdata[b*8 +: 8];
    end

    initial begin
        if (INIT_FILE == "") $fatal(1, "Missing SRAM firmware image");
        for (integer i = 0; i < 2048; i = i + 1) image[i] = 0;
        $readmemh(INIT_FILE, image);
        // Testbench-only program preload through actual memory ports while CPU
        // reset is asserted. No reference to a vendor's internal memory array.
        force dut.i_mainmem.req_i = load_req;
        force dut.i_mainmem.we_i = 1'b1;
        force dut.i_mainmem.be_i = 4'hf;
        force dut.i_mainmem.addr_i = load_addr;
        force dut.i_mainmem.wdata_i = load_data;
        for (integer i = 0; i < 2048; i = i + 1) begin
            @(negedge clk_i);
            load_req = 1; load_addr = 32'h80000000 + i*4; load_data = image[i];
            @(posedge clk_i); #2;
        end
        @(negedge clk_i);
        load_req = 0;
        release dut.i_mainmem.req_i;
        release dut.i_mainmem.we_i;
        release dut.i_mainmem.be_i;
        release dut.i_mainmem.addr_i;
        release dut.i_mainmem.wdata_i;
        repeat (8) @(negedge clk_i);
        rst_ni = 1;
        while (cycle_count < 1000000) begin
            @(posedge clk_i); #2;
            cycle_count = cycle_count + 1;
            if (magic_status === 32'hc0dec0de) begin
                if(result_count!=24) $fatal(1,"Missing results");
                $display("PASS: SRAM SoC self-check OK after %0d cycles", cycle_count);
                $finish;
            end
            if (magic_status === 32'hdeadbeef) $fatal(1, "CPU self-check failed");
        end
        $fatal(1, "SRAM SoC timeout");
    end
endmodule
