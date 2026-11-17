# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 200B; remaining SRAM 6264B.

Task segment 0: base 0x80001940, COUNT=2

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 64/9/2 | 0x80001f38 | 0x80001ac4 | 0x00000000 | NONE | 1/0/0 | 0 |
| 1 | FC | 1/9/2 | 0x80001f78 | 0x80001ec4 | 0x80001f08 | TANH | 0/1/0 | 0 |

