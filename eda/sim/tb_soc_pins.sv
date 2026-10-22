`timescale 1ns/1ps
// The same testbench drives RTL and mapped netlists through package pins only.
// Host image storage below never initializes or forces a DUT memory/register.
module tb_soc_pins #(
    parameter INIT_FILE = "",
    parameter SDF_FILE = "",
    parameter SDF_CORNER = "MAXIMUM",
    parameter real CLK_PERIOD_NS = 20.0,
    parameter real TCK_PERIOD_NS = 100.0,
    parameter integer BOOTS = 2,
    parameter integer CORRUPT_WORD = -1,
    parameter integer EXPECT_DMA = 0,
    parameter integer BENCHMARK = 0,
    parameter integer QUIET_CYCLES = 100000,
    parameter integer MAX_POLLS = 2000,
    parameter real WATCHDOG_NS = 250000000.0
);
    logic clk_i = 0, rst_ni = 0, tck_i = 0, tms_i = 1, td_i = 0;
    wire td_o;
    my_soc_top dut (.clk_i(clk_i), .rst_ni(rst_ni), .tck_i(tck_i),
        .tms_i(tms_i), .td_i(td_i), .td_o(td_o));
    always #(CLK_PERIOD_NS/2.0) clk_i = ~clk_i;

    logic [31:0] image [0:2047];
    logic [31:0] value;
    logic [40:0] scan_value;
    logic discard;
    integer dmi_count = 0, words_written = 0, words_verified = 0;
    integer trace;

    initial begin
        if (SDF_FILE != "") begin
            $display("PIN_SDF_REQUEST file=%s corner=%s", SDF_FILE, SDF_CORNER);
            $sdf_annotate(SDF_FILE, dut, , "sdf_annotation.log", SDF_CORNER);
        end
    end

    // TAP TDO changes on falling TCK. Drive TMS/TDI just after that edge and
    // sample at the end of the next low half-cycle, before the rising edge.
    task automatic tick(input logic tms, tdi, output logic tdo);
        tck_i = 0; tms_i = tms; td_i = tdi;
        #(TCK_PERIOD_NS/2.0); tdo = td_o; tck_i = 1;
        #(TCK_PERIOD_NS/2.0); tck_i = 0;
    endtask
    task automatic idle(input integer count);
        for (integer k=0; k<count; k++) tick(0, 0, discard);
    endtask
    task automatic ir(input logic [4:0] instruction);
        tick(1,0,discard); tick(1,0,discard); tick(0,0,discard); tick(0,0,discard);
        for (integer k=0; k<5; k++) tick(k==4, instruction[k], discard);
        tick(1,0,discard); tick(0,0,discard);
    endtask
    task automatic dr(input integer bits, input logic [40:0] data,
                       output logic [40:0] result);
        result = 0;
        tick(1,0,discard); tick(0,0,discard); tick(0,0,discard);
        for (integer k=0; k<bits; k++) tick(k==bits-1, data[k], result[k]);
        tick(1,0,discard); tick(0,0,discard);
    endtask
    task automatic dmi(input logic [1:0] operation, input logic [6:0] address,
                        input logic [31:0] data, output logic [31:0] result);
        logic [40:0] response;
        dr(41, {address,data,operation}, response);
        idle(16);
        dr(41, 41'd0, response);
        idle(3);
        dmi_count++;
        if (response[1:0] !== 0)
            $fatal(1, "DMI response op=%0d addr=%02x response=%011x", operation,address,response);
        result = response[33:2];
        $fdisplay(trace, "%0t,%0d,%02x,%08x,%08x", $time,operation,address,data,result);
    endtask
    task automatic dw(input logic [6:0] a, input logic [31:0] d);
        logic [31:0] unused_value;
        dmi(2,a,d,unused_value);
    endtask
    task automatic rd(input logic [6:0] a, output logic [31:0] d);
        dmi(1,a,0,d);
    endtask
    task automatic check_sb;
        logic [31:0] status;
        rd(7'h38,status);
        for (integer k=0; k<20 && status[21]; k++) rd(7'h38,status);
        if ((status & 32'h00607000) !== 0)
            $fatal(1,"SBA busy/error sbcs=%08x",status);
    endtask
    task automatic mem_read(input logic [31:0] a, output logic [31:0] d);
        dw(7'h39,a); rd(7'h3c,d);
    endtask
    task automatic halt_cpu;
        // Assert ndmreset first so halt does not depend on uninitialized SRAM.
        dw(7'h10,32'h80000003);
        dw(7'h10,32'h80000001);
        rd(7'h11,value);
        // Unknown status is not an acknowledgement; poll to the same deadline.
        for (integer k=0; k<100 && value[9:8] !== 2'b11; k++) rd(7'h11,value);
        if (value[9:8] !== 2'b11) $fatal(1,"CPU did not halt: dmstatus=%08x",value);
        $display("PIN_CPU_HALTED dmstatus=%08x",value);
    endtask
    task automatic clear_completion;
        // A fresh boot cannot pass because of a previous boot's magic value.
        dw(7'h38,32'h00040000); dw(7'h39,32'h80001fe0); dw(7'h3c,0);
        check_sb(); dw(7'h38,32'h00140000); mem_read(32'h80001fe0,value);
        if (value !== 0) $fatal(1,"failed to clear previous CPU result");
    endtask
    task automatic diagnostics;
        for (integer k=0; k<5; k++) begin
            mem_read(32'h80001fe4 + 32'(4*k),value);
            $display("PIN_CPU_DIAGNOSTIC index=%0d value=%08x",k,value);
        end
    endtask

    initial begin
        if (INIT_FILE=="") $fatal(1,"missing firmware");
        if (CLK_PERIOD_NS<=0 || TCK_PERIOD_NS<=0 || BOOTS<1)
            $fatal(1,"invalid simulation parameters");
        trace = $fopen("jtag_dmi_trace.csv","w");
        if (!trace) $fatal(1,"cannot open DMI trace");
        $fdisplay(trace,"time_ps,operation,dmi_address,write_data,response_data");
        for (integer i=0; i<2048; i++) image[i]='x;
        $readmemh(INIT_FILE,image);
        for (integer i=0; i<2048; i++)
            if (^image[i] === 1'bx) $fatal(1,"missing/unknown image word %0d",i);
        $display("PIN_CONFIG sys_period_ns=%0.3f tck_period_ns=%0.3f boots=%0d",CLK_PERIOD_NS,TCK_PERIOD_NS,BOOTS);
        repeat(8) @(negedge clk_i); rst_ni=1;
        // Avoid an artificial exact edge coincidence between unrelated clocks.
        // Both clocks retain their specified 20 ns / 100 ns periods.
        #(CLK_PERIOD_NS/4.0);
        repeat(6) tick(1,0,discard); tick(0,0,discard);
        dr(32,0,scan_value);
        if (scan_value[31:0] !== 32'h00000001) $fatal(1,"IDCODE=%08x",scan_value[31:0]);
        ir(5'h10); dr(32,0,scan_value);
        if (scan_value[9:4] !== 7 || scan_value[3:0] !== 1) $fatal(1,"DTMCS=%08x",scan_value[31:0]);
        $display("PIN_TAP_PASS idcode=00000001 dtmcs=%08x",scan_value[31:0]);
        ir(5'h11); dw(7'h10,1); halt_cpu();

        dw(7'h38,32'h00050000); dw(7'h39,32'h80000000);
        for (integer i=0; i<2048; i++) begin
            dw(7'h3c,image[i] ^ (i==CORRUPT_WORD ? 32'd1 : 32'd0)); words_written++;
            if (i%256==255) begin check_sb(); $display("PIN_LOAD words=%0d",i+1); end
        end
        dw(7'h38,32'h00140000);
        for (integer i=0; i<2048; i++) begin
            mem_read(32'h80000000+32'(4*i),value);
            if (value !== image[i])
                $fatal(1,"SRAM verify word=%0d got=%08x expected=%08x",i,value,image[i]);
            words_verified++;
        end
        check_sb(); $display("PIN_IMAGE_VERIFIED words=%0d",words_verified);

        // At power-on the CPU waits in a boot-RAM self-loop. Once the entire
        // SRAM image is verified and the CPU is halted, publish the launch
        // instruction through the real SBA path. Ndmreset preserves boot RAM.
        mem_read(32'h00010000,value);
        if (value !== 32'h0000006f) $fatal(1,"missing power-on boot wait loop: %08x",value);
        mem_read(32'h00010004,value);
        if (value !== 32'h00028293) $fatal(1,"unexpected boot ADDI instruction: %08x",value);
        mem_read(32'h00010008,value);
        if (value !== 32'h00028067) $fatal(1,"unexpected boot JALR instruction: %08x",value);
        dw(7'h38,32'h00040000); dw(7'h39,32'h00010000); dw(7'h3c,32'h800002b7);
        check_sb(); dw(7'h38,32'h00140000); mem_read(32'h00010000,value);
        if (value !== 32'h800002b7) $fatal(1,"boot launch instruction readback failed: %08x",value);
        check_sb(); $display("PIN_BOOT_VECTOR_READY address=00010000 instruction=%08x",value);

        for (integer run=0; run<BOOTS; run++) begin
            clear_completion();
            dw(7'h10,3); // reset CPU, interconnect, DMA, NPU, retaining SRAM/debug
            dw(7'h10,1); // execute the actual reset boot ROM and downloaded firmware
            repeat(QUIET_CYCLES) @(negedge clk_i);
            value=0;
            for (integer k=0; k<MAX_POLLS && value !== 32'hc0dec0de; k++) begin
                mem_read(32'h80001fe0,value);
                if (value === 32'hdeadbeef) begin
                    diagnostics(); $fatal(1,"CPU firmware self-check failed run=%0d",run);
                end
            end
            check_sb();
            if (value !== 32'hc0dec0de) begin
                diagnostics(); $fatal(1,"CPU boot timeout run=%0d",run);
            end
            $display("PIN_CPU_PASS run=%0d magic=%08x",run,value);
            if (BENCHMARK) begin
                for (integer m=0; m<5; m++) begin
                    mem_read(32'h80001fc0+32'(4*m),value);
                    if (^value === 1'bx || (m==3 ? (EXPECT_DMA ? value==0 : value!=0) : value==0))
                        $fatal(1,"invalid CPU benchmark metric=%0d cycles=%08x",m,value);
                    $display("PIN_BENCH run=%0d metric=%0d cycles=%0d",run,m,value);
                end
                check_sb();
            end
        end
        $display("SOC_PINS PASS downloaded_words=%0d verified_words=%0d boots=%0d dmi_transactions=%0d",words_written,words_verified,BOOTS,dmi_count);
        $fclose(trace); $finish;
    end
    initial begin #(WATCHDOG_NS); $fatal(1,"pin-level JTAG watchdog"); end
endmodule
