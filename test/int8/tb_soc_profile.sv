`timescale 1ns/1ps
`include "tb_soc.sv"

// Passive companion to the unmodified functional testbench. Compile with
// +incdir+<repo>/test/int8 and -top tb_soc_profile.
//
// Boundaries are real accepted hardware operations, not instruction fetch PCs:
//   fetch: first firmware request; start: accepted NPU start; done: NPU output
//   becomes valid; completion: success word accepted by the SRAM interface.
// Tick differences are disjoint and sum to elapsed_cycles. "post" includes
// finishing the poll, reading every golden result, and publishing counters.
//
// minstret_events is the existing CV32E40P architectural instruction-count
// event. The core implements it at legal ID issue, with CSR semantics making
// it correspond to retired instruction counting (cv32e40p_id_stage.sv).
// This monitor does NOT count requests to the instruction cache, and does not
// modify mcountinhibit (whose reset value inhibits the actual CSR counter).
// Event phases are wall-clock windows, not a reconstructed retirement trace.
module tb_soc_profile;
    tb_soc base();

`define PROF_CPU base.dut.i_cpu.core_i
`define PROF_NPU base.dut.i_npu_subsystem.i_npu_core

    integer tick=0, fetch_tick=-1, start_tick=-1, done_tick=-1;
    integer phase=0;
    integer retired[0:2], loads[0:2], stores[0:2], branches[0:2];
    integer ld_hazards[0:2], imiss_cycles[0:2], jumps[0:2];
    integer compressed=0, input_writes=0, result_reads=0;
    integer i, total_retired, total_loads, total_stores, total_branches;
    integer total_ld_hazards, total_imiss, total_jumps;
    bit active=0, finished=0, done_before=0, complete_now=0;

    initial begin
        for(i=0;i<3;i=i+1) begin
            retired[i]=0; loads[i]=0; stores[i]=0; branches[i]=0;
            ld_hazards[i]=0; imiss_cycles[i]=0; jumps[i]=0;
        end
    end

    always @(posedge base.clk) begin
        tick=tick+1;
        if(!finished && base.dut.firmware_fetch_start && !active) begin
            active=1;
            fetch_tick=tick;
        end
        if(active && !finished) begin
            if(`PROF_NPU.start) begin
                if(start_tick>=0) $fatal(1,"PROFILE unexpected second NPU start");
                start_tick=tick;
                phase=1;
            end
            // These registered event outputs directly feed the CPU CSR block.
            if(`PROF_CPU.mhpmevent_minstret) retired[phase]=retired[phase]+1;
            if(`PROF_CPU.mhpmevent_load) loads[phase]=loads[phase]+1;
            if(`PROF_CPU.mhpmevent_store) stores[phase]=stores[phase]+1;
            if(`PROF_CPU.mhpmevent_branch) branches[phase]=branches[phase]+1;
            if(`PROF_CPU.mhpmevent_jump) jumps[phase]=jumps[phase]+1;
            if(`PROF_CPU.mhpmevent_ld_stall) ld_hazards[phase]=ld_hazards[phase]+1;
            if(`PROF_CPU.mhpmevent_imiss) imiss_cycles[phase]=imiss_cycles[phase]+1;
            if(`PROF_CPU.mhpmevent_compressed) compressed=compressed+1;
            if(base.dut.npu_req) begin
                // The AXI user tag identifies DMA writes; it has no meaning
                // for reads. The DMA only reads SRAM, so all NPU reads are CPU.
                if(base.dut.npu_we && !base.dut.npu_user && start_tick<0) input_writes=input_writes+1;
                if(!base.dut.npu_we && done_tick>=0) result_reads=result_reads+1;
            end
            done_before=`PROF_NPU.done;
            complete_now=base.dut.sram_req && base.dut.sram_we &&
                         base.dut.sram_addr==32'h80001fe0 &&
                         base.dut.sram_wdata==32'hc0dec0de;
            // Observe synchronous done after NBA; start and SRAM write above
            // were sampled before the edge at which the requests were accepted.
            #1;
            if(!done_before && `PROF_NPU.done) begin
                if(start_tick<0 || done_tick>=0) $fatal(1,"PROFILE invalid NPU done");
                done_tick=tick;
                phase=2;
                if(done_tick-start_tick != `PROF_NPU.core.cycle_count)
                    $fatal(1,"PROFILE NPU interval disagrees with hardware counter");
            end
            if(complete_now) begin
                if(fetch_tick<0 || start_tick<0 || done_tick<0)
                    $fatal(1,"PROFILE missing boundary");
                total_retired=0; total_loads=0; total_stores=0;
                total_branches=0; total_ld_hazards=0; total_imiss=0; total_jumps=0;
                for(i=0;i<3;i=i+1) begin
                    total_retired=total_retired+retired[i];
                    total_loads=total_loads+loads[i];
                    total_stores=total_stores+stores[i];
                    total_branches=total_branches+branches[i];
                    total_ld_hazards=total_ld_hazards+ld_hazards[i];
                    total_imiss=total_imiss+imiss_cycles[i];
                    total_jumps=total_jumps+jumps[i];
                end
                $display("INT8_PROFILE elapsed_cycles=%0d setup_cycles=%0d npu_cycles=%0d post_npu_cycles=%0d minstret_events=%0d load_events=%0d store_events=%0d branch_events=%0d jump_events=%0d load_use_events=%0d imiss_cycles=%0d compressed_events=%0d config_writes=%0d post_npu_reads=%0d setup_minstret=%0d npu_minstret=%0d post_minstret=%0d setup_load_use=%0d npu_load_use=%0d post_load_use=%0d setup_imiss=%0d npu_imiss=%0d post_imiss=%0d",
                    tick-fetch_tick,start_tick-fetch_tick,done_tick-start_tick,tick-done_tick,
                    total_retired,total_loads,total_stores,total_branches,total_jumps,
                    total_ld_hazards,total_imiss,compressed,input_writes,result_reads,
                    retired[0],retired[1],retired[2],ld_hazards[0],ld_hazards[1],ld_hazards[2],
                    imiss_cycles[0],imiss_cycles[1],imiss_cycles[2]);
                finished=1;
            end
        end
    end

`undef PROF_CPU
`undef PROF_NPU
endmodule
