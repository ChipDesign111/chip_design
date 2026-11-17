# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 952B; remaining SRAM 5640B.

Task segment 0: base 0x80001a00, COUNT=2

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 17/12/1 | 0x80001fac | 0x80001e00 | 0x80001f94 | RELU | 1/1/0 | 0 |
| 1 | ACTIVATION | 0/12/1 | 0x80001f94 | 0x00000000 | 0x80001f88 | SIGMOID | 0/1/0 | 0 |

CPU: mul (mul); CPU operator kernel

CPU: add (add); CPU operator kernel

Task segment 1: base 0x800019c0, COUNT=1

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 12/5/1 | 0x80001f70 | 0x80001c8c | 0x80001f68 | NONE | 1/1/0 | 327680 |

CPU: mul_1 (mul); CPU operator kernel

CPU: add_1 (add); CPU operator kernel

CPU: softmax (softmax); CPU operator kernel

