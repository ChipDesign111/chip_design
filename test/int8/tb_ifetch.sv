`timescale 1ns/1ps
`include "axi/typedef.svh"

module tb_ifetch;
    `AXI_TYPEDEF_ALL(axi, logic [31:0], logic [3:0], logic [31:0], logic [3:0], logic)
    logic clk=0, rst_n=0, req=0, invalidate=0;
    logic write_valid=0;
    logic [31:0] write_address=0;
    logic [3:0] write_strobes=4'hf;
    logic selective_memory=0;
    integer line_version[256];
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
        .snoop_valid_i(write_valid && (|write_strobes)),
        // Same physical alias normalization as the SoC memory boundary.
        .snoop_addr_i(32'h80000000 | (write_address & 32'h1fff)),
`endif
        .gnt_o(grant), .valid_o(valid), .rdata_o(data),
        .axi_req_o(bus_req), .axi_resp_i(bus_rsp)
    );

    function automatic logic [31:0] memory_word(input logic [31:0] addr, input integer version);
        if (selective_memory && addr>=32'h80000000 && addr<32'h90000000)
            addr=32'h80000000 | (addr & 32'h1fff);
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
                burst_index<=0;
                burst_epoch<=selective_memory ? line_version[bus_req.ar.addr[12:5]] : epoch;
                bursts=bursts+1;
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
        if ($isunknown({grant,valid})) $fatal(1,"IFETCH_FAIL unknown_control");
        if (valid && $isunknown(data)) $fatal(1,"IFETCH_FAIL unknown_valid_data");
        if (rst_n && valid) responses=responses+1;
    end

    task automatic reset_device;
        @(negedge clk); req=0; invalidate=0; write_valid=0; rst_n=0;
        force_ar_hold=0; force_r_hold=0;
        repeat(3) @(negedge clk);
        if (grant!==1'b0 || valid!==1'b0) $fatal(1,"IFETCH_FAIL reset_response");
        rst_n=1;
        repeat(2) @(negedge clk);
    endtask

    task automatic write_line(input logic [31:0] addr, input integer version,
                              input logic [3:0] strobes=4'hf);
        @(negedge clk); write_address=addr; write_strobes=strobes; write_valid=1;
        if (strobes!=0) line_version[addr[12:5]]=version;
        @(negedge clk); write_valid=0;
    endtask

    task automatic checked_hit(input logic [31:0] addr, input integer version);
        integer before_grants,before_responses;
        before_grants=grants; before_responses=responses;
        @(negedge clk); req=1; address=addr;
        @(posedge clk);
        if (!grant) $fatal(1,"IFETCH_FAIL unrelated_write_evicted_line");
        #2;
        if (!valid || data!==memory_word(addr,version))
            $fatal(1,"IFETCH_FAIL checked_hit_wrong_data");
        @(negedge clk); req=0;
        repeat(2) @(negedge clk);
        if (grants-before_grants!=1 || responses-before_responses!=1)
            $fatal(1,"IFETCH_FAIL checked_hit_response_count");
        checks=checks+1;
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

        // Per-line memory versions make unrelated-write preservation and
        // stale-refill cancellation independent of global invalidation tests.
        reset_device;
        selective_memory=1;
        for (integer n=0;n<256;n=n+1) line_version[n]=20;
        fetch(32'h8000101c,20);
        fetch(32'h8000103c,20);
        write_line(32'h80001f00,21);
        checked_hit(32'h80001000,20);
        checked_hit(32'h80001020,20);
        write_line(32'h80001000,22,0);
        checked_hit(32'h80001000,20);
        // A byte write through an alias maps to the canonical cached line.
        write_line(32'h80003004,21,4'b0010);
        checked_hit(32'h80001020,20);
        fetch(32'h80001004,21);

        // No old hit may grant in the very cycle of a matching write.
        @(negedge clk);
        address=32'h80001004;req=1;
        write_address=32'h80001004;write_strobes=4'hf;write_valid=1;
        line_version[32'h1004>>5]=22;
        @(posedge clk);
        if (grant) $fatal(1,"IFETCH_FAIL stale_grant_during_write");
        @(negedge clk); req=0;write_valid=0;
        fetch(32'h80001004,22);

        // A matching write must not withdraw a stalled AR, but the eventual
        // response is killed. A second transaction reads the new version.
        reset_device;
        force_ar_hold=1;
        fork
            fetch(32'h8000111c,21);
            begin
                wait(bus_req.ar_valid);
                write_line(32'h80003100,21);
                repeat(3) @(negedge clk);force_ar_hold=0;
            end
        join

        // Cancel a fill after it has already published two words. The frozen
        // old burst must drain; its later words cannot restore the old line.
        reset_device;
        fork
            fetch(32'h8000121c,21);
            begin
                wait(active && burst_address==32'h80001200 && burst_index==2);
                if (!dut.svalid_q[dut.fill_slot_q])
                    $fatal(1,"IFETCH_FAIL selective_partial_line_missing");
                write_line(32'h80003200,21);
            end
        join
        fetch(32'h80001200,21);

        // An unrelated write while R is stalled must leave this fill intact.
        reset_device;
        force_r_hold=1;
        fork
            fetch(32'h8000131c,20);
            begin
                wait(active);
                write_line(32'h80001f00,23);
                repeat(3) @(negedge clk);force_r_hold=0;
            end
        join

        // A matching write coincident with a new miss defers the request;
        // there is no stale AR transaction whose refill could be published.
        reset_device;
        @(negedge clk);req=1;address=32'h8000141c;
        write_valid=1;write_address=32'h80003400;write_strobes=4'hf;
        line_version[32'h1400>>5]=21;
        @(posedge clk);
        if (grant || bus_req.ar_valid) $fatal(1,"IFETCH_FAIL started_matching_write_fill");
        @(negedge clk);req=0;write_valid=0;
        fetch(32'h8000141c,21);

        // The reverse alias direction matters too: an uncached fetch through
        // 800020xx must be revoked by a canonical write to the same SRAM.
        reset_device;
        force_r_hold=1;
        fork
            fetch(32'h80003504,21);
            begin
                wait(active);
                write_line(32'h80001504,21);
                repeat(3) @(negedge clk);force_r_hold=0;
            end
        join

        // Hold the CPU request away while its single-word response arrives,
        // then modify that physical address before consuming the transient.
        reset_device;
        force_r_hold=1;
        @(negedge clk);req=1;address=32'h80003604;
        wait(active);
        @(negedge clk);req=0;force_r_hold=0;
        wait(dut.single_valid_q);
        write_line(32'h80001604,21);
        fetch(32'h80003604,21);
        $display("IFETCH_PASS checks=%0d grants=%0d responses=%0d bursts=%0d",checks,grants,responses,bursts);
        $finish;
    end
    initial begin #1000000; $fatal(1,"IFETCH_FAIL watchdog"); end
endmodule
