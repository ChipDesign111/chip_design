# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 1068B; remaining SRAM 5848B.

CPU: fc1 (linear); Forced CPU backend

CPU: relu (relu); CPU operator kernel

CPU: sigmoid (sigmoid); CPU operator kernel

CPU: mul (mul); CPU operator kernel

CPU: add (add); CPU operator kernel

CPU: fc2 (linear); Forced CPU backend

CPU: mul_1 (mul); CPU operator kernel

CPU: add_1 (add); CPU operator kernel

CPU: softmax (softmax); CPU operator kernel

