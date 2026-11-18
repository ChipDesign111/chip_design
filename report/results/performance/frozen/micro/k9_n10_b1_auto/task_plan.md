# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 200B; remaining SRAM 7608B.

Task segment 0: base 0x80001e80, COUNT=1

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 9/10/1 | 0x80001fb4 | 0x80001ee0 | 0x80001fa8 | NONE | 1/1/0 | 0 |

