`timescale 1ns/1ps
`include "axi/typedef.svh"

module tb_ifetch;
    `AXI_TYPEDEF_ALL(axi, logic [31:0], logic [3:0], logic [31:0], logic [3:0], logic)
    logic clk=0, rst_n=0, req=0, invalidate=0;
    logic [31:0] address=0;
    wire grant, valid;
    wire [31:0] data;
    axi_req_t bus_req;
    axi_resp_t bus_rsp;
    integer checks=0, cycle=0, grants=0, responses=0, bursts=0;
    integer epoch=0, burst_epoch=0, burst_index=0, burst_words=0;
    logic [31:0] burst_address=0, last_request_address=0;
    logic active=0, read_valid=0, read_last=0;
    logic [31:0] read_data=0;
    axi_pkg::resp_t read_resp=axi_pkg::RESP_OKAY;
    integer inject_fault=0, burst_fault=0;
    logic force_ar_hold=0, force_r_hold=0;
    logic ar_stalled=0;
    axi_ar_chan_t held_ar;

    always #5 clk=~clk;
    my_ifetch #(.axi_req_t(axi_req_t), .axi_rsp_t(axi_resp_t),
        .LINE_WORDS(8), .SLOTS(4), .SRAM_BASE(32'h80000000),
        .SRAM_LENGTH(32'h2000), .BOOT_BASE(32'h10000), .BOOT_LENGTH(32'h20)) dut (
        .clk_i(clk), .rst_ni(rst_n), .req_i(req), .addr_i(address),
`ifndef IFETCH_LEGACY
        .invalidate_i(invalidate),
`endif
        .gnt_o(grant), .valid_o(valid), .rdata_o(data),
        .axi_req_o(bus_req), .axi_resp_i(bus_rsp)
    );

    function automatic logic [31:0] memory_word(input logic [31:0] addr, input integer version);
        return addr ^ (32'h9e3779b9 * (version+1));
    endfunction

    always_comb begin
        bus_rsp='0;
        bus_rsp.ar_ready=rst_n && !active && !force_ar_hold && cycle%4!=0;
        bus_rsp.r_valid=read_valid;
        bus_rsp.r.data=read_data;
        bus_rsp.r.last=read_last;
        bus_rsp.r.id=0;
        bus_rsp.r.resp=read_resp;
    end

    // Frozen burst contents make invalidation during a fill observable.
    // Both request and response channels experience independent backpressure.
    always @(posedge clk) begin
        cycle<=cycle+1;
        if (!rst_n) begin
            active<=0; read_valid<=0; read_last<=0;
            burst_index<=0; ar_stalled<=0;
        end else begin
            if (ar_stalled && (!bus_req.ar_valid || bus_req.ar!==held_ar))
                $fatal(1,"IFETCH_FAIL unstable_AR");
            ar_stalled<=bus_req.ar_valid && !bus_rsp.ar_ready;
            if (bus_req.ar_valid && !bus_rsp.ar_ready) held_ar<=bus_req.ar;
            if (bus_req.aw_valid || bus_req.w_valid)
                $fatal(1,"IFETCH_FAIL unexpected_write");
            if (bus_req.ar_valid && bus_rsp.ar_ready) begin
                if (active || read_valid) $fatal(1,"IFETCH_FAIL overlapping_transaction");
                if (bus_req.ar.size!=2 || bus_req.ar.burst!=axi_pkg::BURST_INCR)
                    $fatal(1,"IFETCH_FAIL invalid_transfer_format");
                if (bus_req.ar.len!=0 && bus_req.ar.len!=7)
                    $fatal(1,"IFETCH_FAIL invalid_burst_length");
                if (bus_req.ar.len!=0 && bus_req.ar.addr[4:0]!=0)
                    $fatal(1,"IFETCH_FAIL unaligned_line");
                if (bus_req.ar.len!=0 && !(bus_req.ar.addr==32'h10000 ||
                    (bus_req.ar.addr>=32'h80000000 && bus_req.ar.addr<=32'h80001fe0)))
                    $fatal(1,"IFETCH_FAIL burst_outside_memory");
                active<=1; burst_address<=bus_req.ar.addr;
                last_request_address<=bus_req.ar.addr;
                burst_words<=inject_fault==2 ? 3 : inject_fault==3 ? 9 : int'(bus_req.ar.len)+1;
                burst_fault<=inject_fault; inject_fault=0;
                burst_index<=0; burst_epoch<=epoch; bursts=bursts+1;
            end
            if (read_valid && bus_req.r_ready) begin
                read_valid<=0;
                if (read_last) active<=0;
                else burst_index<=burst_index+1;
            end else if (active && !read_valid && !force_r_hold && cycle%3!=0) begin
                read_valid<=1;
                read_data<=memory_word(burst_address+4*burst_index,burst_epoch);
                read_last<=burst_index==burst_words-1;
                read_resp<=burst_fault==1 && (burst_index==1 || burst_words==1) ?
                           axi_pkg::RESP_SLVERR : axi_pkg::RESP_OKAY;
            end
            if (req && grant) grants=grants+1;
        end
        #1;
        if (rst_n && valid) responses=responses+1;
    end

    task automatic reset_device;
        @(negedge clk); req=0; invalidate=0; rst_n=0;
        force_ar_hold=0; force_r_hold=0;
        repeat(3) @(negedge clk);
        if (grant || valid) $fatal(1,"IFETCH_FAIL reset_response");
        rst_n=1;
        repeat(2) @(negedge clk);
    endtask

    task automatic fetch(input logic [31:0] addr, input integer expected_epoch,
                         input logic expect_fault=0);
        integer timeout, old_grants, old_responses;
        logic accepted, returned;
        logic [31:0] expected_data;
        expected_data=expect_fault ? 32'b0 : memory_word(addr,expected_epoch);
        old_grants=grants; old_responses=responses;
        @(negedge clk); req=1; address=addr;
        accepted=0; returned=0; timeout=0;
        while (!accepted && timeout<500) begin
            @(posedge clk);
            accepted=grant;
            #2;
            if (valid) begin
                if (!accepted) $fatal(1,"IFETCH_FAIL response_without_grant");
                if (data!==expected_data)
                    $fatal(1,"IFETCH_FAIL wrong_word addr=%h got=%h expected=%h",addr,data,expected_data);
                returned=1;
            end
            timeout=timeout+1;
        end
        if (!accepted) $fatal(1,"IFETCH_FAIL fetch_timeout addr=%h",addr);
        @(negedge clk); req=0;
        while (!returned && timeout<510) begin
            @(posedge clk); #2;
            if (valid) begin
                if (data!==expected_data)
                    $fatal(1,"IFETCH_FAIL late_wrong_word addr=%h",addr);
                returned=1;
            end
            timeout=timeout+1;
        end
        if (!returned) $fatal(1,"IFETCH_FAIL missing_response");
        repeat(2) @(negedge clk);
        if (grants-old_grants!=1 || responses-old_responses!=1)
            $fatal(1,"IFETCH_FAIL duplicate_response grants=%0d responses=%0d",grants-old_grants,responses-old_responses);
        checks=checks+1;
    endtask

    // Once a whole line is resident, keep req asserted across adjacent hits.
    // Every hit must grant without a bubble and return the corresponding word.
    task automatic stream_hits;
        integer old_grants, old_responses;
        logic [31:0] stream_address;
        old_grants=grants; old_responses=responses;
        for (integer n=0;n<24;n=n+1) begin
            @(negedge clk); req=1; stream_address=32'h80000000+4*(n%8); address=stream_address;
            @(posedge clk);
            if (!grant) $fatal(1,"IFETCH_FAIL buffered_hit_bubble");
            #2;
            if (!valid || data!==memory_word(stream_address,epoch))
                $fatal(1,"IFETCH_FAIL stream_wrong_word");
        end
        @(negedge clk); req=0;
        repeat(2) @(negedge clk);
        if (grants-old_grants!=24 || responses-old_responses!=24)
            $fatal(1,"IFETCH_FAIL stream_duplicate_or_missing_response");
        checks=checks+24;
    endtask

    task automatic invalidate_now;
        @(negedge clk); epoch=epoch+1; invalidate=1;
        @(negedge clk); invalidate=0;
    endtask

    // Invalidation revokes future hits, not a response whose grant was already
    // sampled. Assert it during that response cycle and hold through its end.
    task automatic invalidate_accepted_response;
        integer old_grants, old_responses, old_epoch;
        old_grants=grants; old_responses=responses; old_epoch=epoch;
        @(negedge clk); req=1; address=32'h80000400;
        @(posedge clk);
        if (!grant) $fatal(1,"IFETCH_FAIL accepted_response_not_granted");
        #2;
        if (!valid || data!==memory_word(address,old_epoch))
            $fatal(1,"IFETCH_FAIL accepted_response_missing");
        invalidate=1; epoch=epoch+1;
        #1;
        if (!valid || data!==memory_word(address,old_epoch))
            $fatal(1,"IFETCH_FAIL invalidation_withdrew_response");
        @(negedge clk); req=0;
        @(posedge clk); #2;
        if (valid) $fatal(1,"IFETCH_FAIL accepted_response_duplicated");
        @(negedge clk); invalidate=0;
        if (grants-old_grants!=1 || responses-old_responses!=1)
            $fatal(1,"IFETCH_FAIL accepted_response_count");
        checks=checks+1;
    endtask

    initial begin
        reset_device;
        // Non-cacheable words at nonzero offsets must use their exact address.
        fetch(32'h00000804,0);
        if (last_request_address!==32'h00000804)
            $fatal(1,"IFETCH_FAIL wrong_single_address");
        if ($test$plusargs("ONLY_UNCACHED")) begin
            $display("IFETCH_UNCACHED_PASS checks=%0d",checks); $finish;
        end
        epoch=1; fetch(32'h00000804,1);
        fetch(32'h0000081c,1);
        fetch(32'h0001001c,1);
        fetch(32'h00010004,1);
        fetch(32'h00010024,1);
        fetch(32'h8000001c,1);
        stream_hits;
        fetch(32'h80000000,1);
        fetch(32'h80000024,1);
        fetch(32'h80001ffc,1);
        fetch(32'h80002004,1);
        invalidate_now;
        fetch(32'h80000000,2);

        reset_device;
        force_ar_hold=1;
        fork
            fetch(32'h8000005c,3);
            begin
                wait(bus_req.ar_valid); invalidate_now;
                repeat(3) @(negedge clk);
                force_ar_hold=0;
            end
        join

        reset_device;
        force_r_hold=1;
        fork
            fetch(32'h8000009c,4);
            begin
                wait(active); invalidate_now;
                repeat(3) @(negedge clk);
                force_r_hold=0;
            end
        join
        fetch(32'h80000080,4);

        reset_device;
        force_ar_hold=1;
        @(negedge clk); req=1; address=32'h80000100;
        wait(bus_req.ar_valid);
        reset_device;
        epoch=5; fetch(32'h80000100,5);

        reset_device;
        force_r_hold=1;
        @(negedge clk); req=1; address=32'h8000015c;
        wait(active);
        reset_device;
        epoch=6; fetch(32'h8000015c,6);

        // Revoke a line only after two real response beats have been published.
        // The pending last-word request must survive draining the stale fill
        // and return the new epoch from a subsequent transaction.
        reset_device;
        fork
            fetch(32'h8000031c,7);
            begin
                wait(active && burst_address==32'h80000300 && burst_index==2);
                if (!dut.svalid_q[dut.fill_slot_q])
                    $fatal(1,"IFETCH_FAIL partial_line_not_published");
                invalidate_now;
            end
        join
        fetch(32'h80000300,7);

        reset_device;
        fetch(32'h8000041c,7);
        invalidate_accepted_response;
        fetch(32'h80000400,8);

        // A branch may replace an ungranted request while the previous burst
        // drains. No data from that burst may satisfy the new address.
        reset_device;
        force_r_hold=1;
        @(negedge clk); req=1; address=32'h8000061c;
        wait(active);
        @(negedge clk); req=0; address=32'h8000071c; force_r_hold=0;
        fetch(32'h8000071c,8);
        fetch(32'h8000061c,8);

        // Bus faults must never publish stale or corrupt cache contents.
        // Fetch a late word so an early valid beat cannot satisfy the request.
        for (integer fault=1;fault<=3;fault=fault+1) begin
            reset_device;
            inject_fault=fault;
            fetch(32'h8000021c,epoch,1);
            fetch(32'h8000021c,epoch);
        end
        reset_device;
        inject_fault=1;
        fetch(32'h00000804,epoch,1);
        fetch(32'h00000804,epoch);
        $display("IFETCH_PASS checks=%0d grants=%0d responses=%0d bursts=%0d",checks,grants,responses,bursts);
        $finish;
    end
    initial begin #1000000; $fatal(1,"IFETCH_FAIL watchdog"); end
endmodule
