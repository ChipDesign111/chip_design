`timescale 1ns/1ps

// Lab6-compatible board top for the current HAR SoC.
// The 100 MHz board clock is converted to 50 MHz by clk_wiz_0.
module fpga_top #(
    // Absolute by default because Vivado resolves $readmemh relative paths
    // against its launch directory. Override this parameter if the tree moves.
    parameter SRAM_INIT_FILE =
        "fpga/firmware/int8_selftest.hex"
) (
    input  logic fpga_clk_i,
    input  logic rst_ni,
    input  logic tck_i,
    input  logic tms_i,
    input  logic td_i,
    output logic td_o,
    output logic led_locked,
    output logic led_heartbeat,
    output logic led_tck
);

  localparam [31:0] TEST_RUNNING = 32'h1234_5678;
  localparam [31:0] TEST_PASS    = 32'hC0DE_C0DE;
  localparam [31:0] TEST_FAIL    = 32'hDEAD_BEEF;

  logic clk_sys;
  logic clk_locked;

  clk_wiz_0 u_clk_wiz (
      .clk_in1 (fpga_clk_i),
      .clk_out1(clk_sys),
      .locked  (clk_locked)
  );

  wire async_rst_n = rst_ni & clk_locked;
  logic [1:0] rst_sync_q;

  always_ff @(posedge clk_sys or negedge async_rst_n) begin
    if (!async_rst_n) begin
      rst_sync_q <= 2'b00;
    end else begin
      rst_sync_q <= {rst_sync_q[0], 1'b1};
    end
  end

  wire rst_sys_n = rst_sync_q[1];

  my_soc_top #(
      .FPGA_INIT_FILE(SRAM_INIT_FILE)
  ) u_soc (
      .clk_i  (clk_sys),
      .rst_ni (rst_sys_n),
      .tck_i  (tck_i),
      .tms_i  (tms_i),
      .td_i   (td_i),
      .td_o   (td_o)
  );

  // Capture the SoC self-check result written at the top of main SRAM.
  wire test_status_write =
      u_soc.sram_req && u_soc.sram_we && (u_soc.sram_be == 4'hf) &&
      (u_soc.sram_addr == 32'h8000_1FE0);
  logic [31:0] test_status_q;

  always_ff @(posedge clk_sys or negedge rst_sys_n) begin
    if (!rst_sys_n) begin
      test_status_q <= TEST_RUNNING;
    end else if (test_status_write) begin
      test_status_q <= u_soc.sram_wdata;
    end
  end

  // LED meanings while preserving the Lab6 pinout:
  // locked=MMCM locked, heartbeat=solid PASS/fast FAIL/normal otherwise,
  // tck=JTAG clock activity.
  logic [24:0] heartbeat_cnt;
  logic heartbeat;
  always_ff @(posedge clk_sys or negedge rst_sys_n) begin
    if (!rst_sys_n) begin
      heartbeat_cnt <= '0;
      heartbeat     <= 1'b0;
    end else if (heartbeat_cnt == 25'd24_999_999) begin
      heartbeat_cnt <= '0;
      heartbeat     <= ~heartbeat;
    end else begin
      heartbeat_cnt <= heartbeat_cnt + 1'b1;
    end
  end

  logic [21:0] fail_blink_cnt;
  logic fail_blink;
  always_ff @(posedge clk_sys or negedge rst_sys_n) begin
    if (!rst_sys_n) begin
      fail_blink_cnt <= '0;
      fail_blink     <= 1'b0;
    end else if (fail_blink_cnt == 22'd2_499_999) begin
      fail_blink_cnt <= '0;
      fail_blink     <= ~fail_blink;
    end else begin
      fail_blink_cnt <= fail_blink_cnt + 1'b1;
    end
  end

  assign led_locked = clk_locked;
  assign led_heartbeat =
      (test_status_q == TEST_PASS) ? 1'b1 :
      (test_status_q == TEST_FAIL) ? fail_blink : heartbeat;

  logic [18:0] tck_cnt;
  always_ff @(posedge tck_i or negedge rst_ni) begin
    if (!rst_ni) begin
      tck_cnt <= '0;
      led_tck <= 1'b0;
    end else if (tck_cnt == 19'd499_999) begin
      tck_cnt <= '0;
      led_tck <= ~led_tck;
    end else begin
      tck_cnt <= tck_cnt + 1'b1;
    end
  end

endmodule
