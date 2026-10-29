// One reset boundary shared by the SRAM AXI bridge and its command registers.
// Both assertion and release are sampled; neither output stage has an async
// reset connection. The external reset must be held while the clock runs for
// at least two falling edges. Until then the transaction domain is uninitialised.
module sram_transaction_reset (
    input  logic clk_i,
    input  logic reset_request_ni,
    output logic transaction_reset_no
);
    // The first stage is the asynchronous reset-request sampling boundary.
    // Its metastability settling time is one full clock period. These hints
    // do not disable any simulation timing check or create a false path.
    (* async_reg = "true" *) logic reset_sample_n;
    (* async_reg = "true" *) logic reset_qualified_n;
    always_ff @(negedge clk_i) begin
        reset_sample_n    <= reset_request_ni;
        reset_qualified_n <= reset_sample_n;
    end
    assign transaction_reset_no = reset_qualified_n;
endmodule
