// Project-owned zero-input, zero-delay tie-cell simulation views.
// Both native cells have only buf(output, constant), no specify/timing arcs.
// Supply nets establish the same constants at elaboration instead of exposing
// a time-zero delta-cycle X from a primitive buffer to the bidirectional PAD.
// No IO behavior, conflict check, SDF value or timing notifier is modified.
module TIEHBWP7T(output wire Z);
    supply1 Z;
endmodule
module TIELBWP7T(output wire ZN);
    supply0 ZN;
endmodule
