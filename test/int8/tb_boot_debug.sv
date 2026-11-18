`timescale 1ns/1ps

// Run control uses the real JTAG TAP, DMI CDC, Debug Module and Debug ROM.
// Bulk image loading uses the SBA master boundary, as in tb_soc; no CPU,
// halt/resume signal, status register or SRAM array is forced.
module tb_boot_debug;
    reg clk=0, rst_n=0, tck=0, tms=1, tdi=0;
    wire tdo;
    always #5 clk=~clk;
    my_soc_top dut(.clk_i(clk),.rst_ni(rst_n),.tck_i(tck),
                   .tms_i(tms),.td_i(tdi),.td_o(tdo));

    reg load_req=0, load_we=0;
    reg [3:0] load_be=15;
    reg [31:0] load_addr=0, load_data=0, image[0:2047];
    integer passed=0, cases=0, pass_writes=0, boot_reads=0;
    integer n, count, before_pass, before_reads;
    reg [31:0] status, dpc, frozen_cycles;

    always @(posedge clk) begin
        if(dut.ndmreset_n) begin
            if(!dut.boot_ready && !dut.debug_halted && dut.instr_req &&
               dut.instr_addr>=32'h80000000 && dut.instr_addr<32'h80002000)
                $fatal(1,"UNCOMMITTED_SRAM_FETCH pc=%h",dut.instr_addr);
            if(dut.data_req && dut.data_gnt && !dut.data_we &&
               !dut.debug_halted && dut.data_addr==32'h0001003c)
                boot_reads=boot_reads+1;
            if(dut.sram_req && dut.sram_we && dut.sram_be==15 &&
               dut.sram_addr==32'h80001fe0 && dut.sram_wdata==32'hc0dec0de) begin
                if(!dut.boot_ready) $fatal(1,"UNCOMMITTED_PASS_WRITE");
                pass_writes=pass_writes+1;
            end
        end
    end

    task tap_clock(input bit mode, input bit data, output bit result);
        begin
            tms=mode;tdi=data;
            #20;result=tdo;tck=1;
            #20;tck=0;#1;
        end
    endtask

    task tap_idle(input integer clocks);
        bit unused;
        repeat(clocks) tap_clock(0,0,unused);
    endtask

    task tap_ir(input reg [4:0] instruction);
        bit unused;
        integer i;
        begin
            tap_clock(1,0,unused);tap_clock(1,0,unused);
            tap_clock(0,0,unused);tap_clock(0,0,unused);
            for(i=0;i<5;i=i+1) tap_clock(i==4,instruction[i],unused);
            tap_clock(1,0,unused);tap_clock(0,0,unused);
        end
    endtask

    task tap_dr(input reg [40:0] request, output reg [40:0] response);
        bit sampled;
        integer i;
        begin
            tap_clock(1,0,sampled);tap_clock(0,0,sampled);
            tap_clock(0,0,sampled);
            for(i=0;i<41;i=i+1) begin
                tap_clock(i==40,request[i],sampled);
                response[i]=sampled;
            end
            tap_clock(1,0,sampled);tap_clock(0,0,sampled);
        end
    endtask

    task dmi(input reg [6:0] address, input reg [31:0] data,
             input reg [1:0] operation, output reg [31:0] result);
        reg [40:0] response;
        begin
            tap_dr({address,data,operation},response);
            if(response[1:0]!==2'b00) $fatal(1,"DMI request error: %h",response);
            tap_idle(12);
            tap_dr(41'd0,response);
            if(response[1:0]!==2'b00) $fatal(1,"DMI response error: %h",response);
            result=response[33:2];
            tap_idle(4);
        end
    endtask

    task dmi_write(input reg [6:0] address, input reg [31:0] value);
        reg [31:0] unused;
        dmi(address,value,2'b10,unused);
    endtask

    task dmi_read(input reg [6:0] address, output reg [31:0] value);
        dmi(address,0,2'b01,value);
    endtask

    task connect_debug;
        bit unused;
        begin
            repeat(8) tap_clock(1,0,unused);
            tap_clock(0,0,unused);
            tap_ir(5'h11);
            dmi_write(7'h10,32'h00000001);
        end
    endtask

    task wait_status(input reg [31:0] mask, expected);
        reg [31:0] value;
        integer tries;
        begin
            tries=0;
            dmi_read(7'h11,value);
            while((value & mask)!==expected && tries<30) begin
                dmi_read(7'h11,value);tries=tries+1;
            end
            if((value & mask)!==expected)
                $fatal(1,"DM status timeout: got=%h mask=%h expected=%h",value,mask,expected);
        end
    endtask

    task halt_hart;
        begin
            dmi_write(7'h10,32'h80000001);
            wait_status(32'h00003f00,32'h00000300);
            if(!dut.debug_req_irq) $fatal(1,"Halt request did not reach CPU");
            dmi_write(7'h10,32'h00000001);
            repeat(100) @(negedge clk);
            if(dut.debug_req_irq || !dut.debug_halted || !dut.i_dm_top.halted[0])
                $fatal(1,"Clearing haltreq unexpectedly resumed CPU");
        end
    endtask

    task resume_hart;
        begin
            dmi_write(7'h10,32'h40000001);
            wait_status(32'h00030000,32'h00030000);
            dmi_write(7'h10,32'h00000001);
            wait_status(32'h00003f00,32'h00000c00);
            if(dut.debug_halted) $fatal(1,"Resume did not leave Debug Mode");
        end
    endtask

    task abstract_done;
        reg [31:0] value;
        integer tries;
        begin
            tries=0;dmi_read(7'h16,value);
            while(value[12] && tries<30) begin
                dmi_read(7'h16,value);tries=tries+1;
            end
            if(value[12] || value[10:8]!=0)
                $fatal(1,"DEBUG_ABSTRACT_COMMAND_FAILED abstractcs=%h pc=%h halted=%b dm_state=%0d",
                       value,dut.i_cpu.core_i.pc_id,dut.debug_halted,
                       dut.i_dm_top.i_dm_mem.state_q);
        end
    endtask

    task write_register(input reg [15:0] number, input reg [31:0] value);
        begin
            dmi_write(7'h04,value);
            dmi_write(7'h17,32'h00230000 | number);
            abstract_done();
        end
    endtask

    task read_register(input reg [15:0] number, output reg [31:0] value);
        begin
            dmi_write(7'h17,32'h00220000 | number);
            abstract_done();
            dmi_read(7'h04,value);
        end
    endtask

    task sba_write(input reg [31:0] address, value, input reg [3:0] be);
        integer timeout;
        begin
            @(negedge clk);load_req=1;load_we=1;
            load_addr=address;load_data=value;load_be=be;timeout=0;
            @(posedge clk);
            while(!dut.dm_master_gnt && timeout<1000) begin
                @(posedge clk);timeout=timeout+1;
            end
            if(timeout>=1000) $fatal(1,"SBA grant timeout");
            @(negedge clk);load_req=0;timeout=0;
            while(!dut.dm_master_r_valid && timeout<1000) begin
                @(posedge clk);timeout=timeout+1;
            end
            if(timeout>=1000) $fatal(1,"SBA response timeout");
            @(negedge clk);
        end
    endtask

    task physical_reset;
        begin
            @(negedge clk);rst_n=0;
            repeat(12) @(negedge clk);
            rst_n=1;repeat(40) @(negedge clk);
            if(dut.boot_ready || dut.i_bootram.loaded_words!=0)
                $fatal(1,"Physical reset did not clear boot permission/coverage");
        end
    endtask

    task prove_boot_wait;
        integer reads, writes;
        begin
            reads=boot_reads;writes=pass_writes;
            repeat(2000) @(negedge clk);
            if(dut.boot_ready || dut.debug_halted || boot_reads-reads<10 ||
               pass_writes!=writes || dut.i_bootram.soc_cycles!=0)
                $fatal(1,"Boot did not poll safely: ready=%b halted=%b reads=%0d cycles=%0d",
                       dut.boot_ready,dut.debug_halted,boot_reads-reads,dut.i_bootram.soc_cycles);
        end
    endtask

    task case_pass(input string name);
        begin
            cases=cases+1;$display("BOOT_DEBUG_CASE_PASS %s",name);
        end
    endtask

    initial begin
        force dut.dm_master_req=load_req;force dut.dm_master_we=load_we;
        force dut.dm_master_add=load_addr;force dut.dm_master_wdata=load_data;
        force dut.dm_master_be=load_be;
        $readmemh("firmware.hex",image);
        physical_reset();
        for(n=0;n<2048;n=n+1) sba_write(32'h80000000+n*4,image[n],15);
        // Preserve a runnable old image, but clear its coverage and permission.
        physical_reset();
        connect_debug();
        dmi_read(7'h11,status);
        if((status & 32'h00003f00)!==32'h00003000)
            $fatal(1,"RESET_STATE_MISREPORTED dmstatus=%h",status);
        if(dut.instr_req || dut.i_cpu.debug_running_o || dut.debug_halted)
            $fatal(1,"CPU left reset-wait without a request");
        case_pass("preserved_sram_reset_reports_unavailable");

        // Model examine() seeing unavailable: halt for inspection, then keep
        // halted (only an initially running hart gets an automatic resume).
        halt_hart();
        read_register(16'h07b1,dpc);
        if(dpc!==32'h00010000) $fatal(1,"Cold halt DPC=%h",dpc);
        before_pass=pass_writes;
        repeat(2000) @(negedge clk);
        if(!dut.debug_halted || pass_writes!=before_pass || dut.boot_ready)
            $fatal(1,"Initial examination did not keep the hart halted");
        case_pass("cold_halt_and_request_clear_keep_debug_mode");

        // A cold-halted core must stay available for OpenOCD's default progbuf
        // loading path even though boot_ready is zero.
        write_register(16'h1005,32'h80001fd0);
        write_register(16'h1006,32'h5aa55aa5);
        dmi_write(7'h20,32'h0062a023); // sw t1,0(t0)
        dmi_write(7'h21,32'h00100073); // ebreak: return to Debug ROM
        dmi_write(7'h17,32'h00240000); // postexec, no register transfer
        abstract_done();
        dmi_write(7'h20,32'h0002a303); // lw t1,0(t0)
        dmi_write(7'h17,32'h00240000);
        abstract_done();
        read_register(16'h1006,status);
        if(status!==32'h5aa55aa5 || dut.boot_ready)
            $fatal(1,"Cold progbuf SRAM round trip failed: %h",status);
        wait_status(32'h00003f00,32'h00000300);
        case_pass("cold_progbuf_sram_write_read");

        // Deliberately resume before commit. The ROM must poll, not jump into
        // the old image. Check repeated real MMIO reads, not just absence of PASS.
        resume_hart();prove_boot_wait();
        case_pass("uncommitted_resume_polls_boot_status");
        sba_write(32'h0001003c,32'hb007c0de,15);
        sba_write(32'h80001ffc,image[2047],15);
        sba_write(32'h80000000,image[0],3);
        if(dut.i_bootram.loaded_words!=0) $fatal(1,"Invalid writes counted as coverage");
        prove_boot_wait();
        case_pass("key_partial_and_out_of_order_writes_stay_blocked");
        for(n=0;n<2047;n=n+1) sba_write(32'h80000000+n*4,image[n],15);
        sba_write(32'h0001003c,32'hb007c0de,15);
        prove_boot_wait();
        sba_write(32'h80001ffc,image[2047],15);
        if(dut.i_bootram.loaded_words!=2048) $fatal(1,"Full image not covered");
        sba_write(32'h0001003c,32'hdeadbeef,15);
        prove_boot_wait();
        case_pass("full_image_still_requires_valid_commit");

        before_pass=pass_writes;
        sba_write(32'h0001003c,32'hb007c0de,15);
        count=0;
        while(pass_writes==before_pass && count<2000) begin
            @(negedge clk);count=count+1;
        end
        if(pass_writes!=before_pass+1 || !dut.boot_ready ||
           !dut.i_bootram.soc_cycles_captured || dut.i_bootram.soc_cycles==0)
            $fatal(1,"Committed image failed to run from cached boot poll loop");
        frozen_cycles=dut.i_bootram.soc_cycles;
        case_pass("commit_releases_cached_poll_loop_and_captures_cycles");

        halt_hart();read_register(16'h07b1,dpc);
        if(dpc<32'h80000000 || dpc>=32'h80002000)
            $fatal(1,"Post-commit DPC did not point into firmware: %h",dpc);
        write_register(16'h07b1,32'h80000014); // payload's terminal loop
        before_reads=boot_reads;
        resume_hart();repeat(200) @(negedge clk);
        if(boot_reads!=before_reads || dut.i_bootram.soc_cycles!==frozen_cycles)
            $fatal(1,"Post-commit resume lost DPC or changed captured cycles");
        case_pass("post_commit_dpc_resume_preserved");

        halt_hart();
        dmi_write(7'h10,32'h80000003); // ndmreset + haltreq + dmactive
        if(dut.ndmreset_n || !dut.por_reset_n || dut.boot_ready)
            $fatal(1,"NDM reset crossed the wrong reset domain");
        dmi_read(7'h11,status);
        if((status & 32'h00003f00)!==32'h00003000)
            $fatal(1,"NDM reset did not report unavailable: %h",status);
        dmi_write(7'h10,32'h80000001);
        wait_status(32'h00003f00,32'h00000300);
        dmi_write(7'h10,32'h00000001);
        read_register(16'h07b1,dpc);
        if(dpc!==32'h00010000 || dut.i_bootram.loaded_words!=0)
            $fatal(1,"Reset-halt did not restore cold boot entry");
        resume_hart();prove_boot_wait();
        case_pass("ndm_reset_halt_resume_returns_to_guarded_boot");

        halt_hart();physical_reset();connect_debug();
        dmi_read(7'h11,status);
        if((status & 32'h00003f00)!==32'h00003000)
            $fatal(1,"Button reset did not return to unavailable");
        // get_hart_state() reasserts haltreq if OpenOCD had cached HALTED.
        dmi_write(7'h10,32'h90000001); // ackhavereset + haltreq + dmactive
        wait_status(32'h00003f00,32'h00000300);
        dmi_write(7'h10,32'h00000001);
        before_pass=pass_writes;repeat(2000) @(negedge clk);
        if(!dut.debug_halted || dut.boot_ready || pass_writes!=before_pass)
            $fatal(1,"Button reset automatic re-halt ran old firmware");
        case_pass("button_reset_rehalt_stays_halted");

        passed=1;
        $display("BOOT_DEBUG_PASS cases=%0d boot_status_reads=%0d payload_pass_writes=%0d",
                 cases,boot_reads,pass_writes);
        $finish;
    end

    initial begin
        #20000000;$fatal(1,"BOOT_DEBUG_TIMEOUT");
    end
endmodule

module tb_boot_preinitialized;
    reg clk=0, rst_n=0;
    wire tdo;
    integer passed=0, pass_writes=0, n, timeout;
    always #5 clk=~clk;
    my_soc_top #(.FPGA_INIT_FILE("firmware.hex")) dut(
        .clk_i(clk),.rst_ni(rst_n),.tck_i(1'b0),.tms_i(1'b1),
        .td_i(1'b0),.td_o(tdo));
    always @(posedge clk) begin
        if(dut.ndmreset_n && dut.sram_req && dut.sram_we &&
           dut.sram_addr==32'h80001fe0 && dut.sram_wdata==32'hc0dec0de) begin
            if(!dut.boot_ready) $fatal(1,"Preinitialized image ran before ready");
            pass_writes=pass_writes+1;
        end
    end
    initial begin
        for(n=1;n<=2;n=n+1) begin
            #1;rst_n=0;repeat(12) @(negedge clk);rst_n=1;
            timeout=0;
            while(pass_writes<n && timeout<2000) begin
                @(negedge clk);timeout=timeout+1;
            end
            if(pass_writes!=n || !dut.boot_ready || !dut.i_cpu.debug_running_o ||
               dut.i_dm_top.i_dm_csrs.dmstatus.allunavail)
                $fatal(1,"Preinitialized boot failed after reset %0d",n);
        end
        passed=1;$display("BOOT_PREINITIALIZED_PASS resets=2");$finish;
    end
endmodule
