// Project-owned interface-only declaration for generic connectivity checks.
// No implementation, timing, geometry or vendor library content is provided.
(* blackbox *) module RA1SHD_2048x32M8 (
    input CLK, input CEN, input [3:0] WEN,
    input [10:0] A, input [31:0] D,
    input OEN, output [31:0] Q
);
endmodule
