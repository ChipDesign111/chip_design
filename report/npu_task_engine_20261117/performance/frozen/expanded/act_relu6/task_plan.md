# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 200B; remaining SRAM 7608B.

Task segment 0: base 0x80001e80, COUNT=1

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 9/7/4 | 0x80001f90 | 0x80001ee4 | 0x80001f50 | RELU6 | 1/1/0 | 0 |

