# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 200B; remaining SRAM 6776B.

Task segment 0: base 0x80001b40, COUNT=2

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 9/16/4 | 0x80001f90 | 0x80001df0 | internal | SIGMOID | 1/1/1 | 0 |
| 1 | ACTIVATION | 0/16/4 | internal | 0x00000000 | 0x80001ed0 | TANH | 0/1/0 | 0 |

