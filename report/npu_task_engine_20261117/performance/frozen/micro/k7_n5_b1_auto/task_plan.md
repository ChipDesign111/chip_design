# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 200B; remaining SRAM 7736B.

Task segment 0: base 0x80001f00, COUNT=1

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 7/5/1 | 0x80001fb8 | 0x80001f5c | 0x80001fb0 | NONE | 1/1/0 | 0 |

