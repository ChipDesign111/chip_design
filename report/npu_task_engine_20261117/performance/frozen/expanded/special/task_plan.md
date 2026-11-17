# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 784B; remaining SRAM 4344B.

MODE0: _0 -> _1 -> _2

64/32/6, unbranched FC/ReLU/FC, full INT22 safety, exhaustive INT8 ReLU identity, exact UINT16 scale reduction, explicit W2 layout

