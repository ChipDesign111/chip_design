`timescale 1ns/1ps
// SRAM simulation loader and passive CPU-write completion monitor.
module tb_stream_soc #(
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
    reg [31:0] gold[0:1127];
    reg [31:0] dma_overlap_beats=0,dma_compute_overlap=0,dma_transfer_compute_cycles=0;
    reg [31:0] result_count=0,first_result_cycle=0,last_result_cycle=0;
    reg [31:0] min_result_interval=32'hffffffff,max_result_interval=0,stream_window_cycles=0;
    wire [31:0] npu_cycles=dut.i_npu_subsystem.i_npu_core.cycles;
    wire [31:0] npu_fc1_issues=dut.i_npu_subsystem.i_npu_core.fc1_issues;
    wire [31:0] npu_fc2_issues=dut.i_npu_subsystem.i_npu_core.fc2_issues;
    reg [31:0] first_fc1_issue=0,last_fc1_issue=0,first_fc2_issue=0,last_fc2_issue=0;
    reg [31:0] observed_fc1_issues=0,observed_fc2_issues=0;
    integer j;
    initial begin
        if(GOLD_FILE=="") $fatal(1,"Missing GOLD_FILE");
        $readmemh(GOLD_FILE,gold);
    end
    always @(posedge clk_i) if(rst_ni) begin
        if(dut.i_npu_subsystem.i_npu_core.w1_re) begin
            if(observed_fc1_issues==0) first_fc1_issue<=cycle_count;
            last_fc1_issue<=cycle_count;observed_fc1_issues<=observed_fc1_issues+1;
        end
        if(dut.i_npu_subsystem.i_npu_core.w2_re) begin
            if(observed_fc2_issues==0) first_fc2_issue<=cycle_count;
            last_fc2_issue<=cycle_count;observed_fc2_issues<=observed_fc2_issues+1;
        end
        if(dut.slave[3].r_valid && dut.slave[3].r_ready && dut.slave[3].w_valid && dut.slave[3].w_ready)
            dma_overlap_beats<=dma_overlap_beats+1;
        if(dut.dma_busy && (dut.i_npu_subsystem.i_npu_core.w1_re || dut.i_npu_subsystem.i_npu_core.w2_re))
            dma_compute_overlap<=dma_compute_overlap+1;
        if((dut.i_npu_subsystem.i_npu_core.w1_re || dut.i_npu_subsystem.i_npu_core.w2_re) &&
           ((dut.slave[3].r_valid && dut.slave[3].r_ready) || (dut.slave[3].w_valid && dut.slave[3].w_ready)))
            dma_transfer_compute_cycles<=dma_transfer_compute_cycles+1;
        if(dut.i_npu_subsystem.i_npu_core.result_valid) begin
            if(dut.i_npu_subsystem.i_npu_core.result_id!=result_count || result_count>=24)
                $fatal(1,"Stream frame order");
            for(j=0;j<32;j=j+1)
                if(dut.i_npu_subsystem.i_npu_core.result_hidden[j*8+:8]!==gold[result_count*47+8+j][7:0])
                    $fatal(1,"Stream hidden mismatch frame=%0d row=%0d",result_count,j);
            for(j=0;j<6;j=j+1)
                if(dut.i_npu_subsystem.i_npu_core.result_scores[j*32+:32]!==gold[result_count*47+40+j])
                    $fatal(1,"Stream score mismatch frame=%0d row=%0d",result_count,j);
            if(dut.i_npu_subsystem.i_npu_core.result_class!==gold[result_count*47+46][2:0])
                $fatal(1,"Stream class mismatch");
            if(result_count==0) first_result_cycle<=cycle_count;
            else begin
                if(cycle_count-last_result_cycle<min_result_interval) min_result_interval<=cycle_count-last_result_cycle;
                if(cycle_count-last_result_cycle>max_result_interval) max_result_interval<=cycle_count-last_result_cycle;
            end
            last_result_cycle<=cycle_count;result_count<=result_count+1;
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
                32'h80001fd4:stream_window_cycles<=dut.sram_wdata;
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
                if(result_count!=24) $fatal(1,"Missing stream results");
                $display("PASS: SRAM SoC self-check OK after %0d cycles", cycle_count);
                $finish;
            end
            if (magic_status === 32'hdeadbeef) $fatal(1, "CPU self-check failed");
        end
        $fatal(1, "SRAM SoC timeout");
    end
endmodule
