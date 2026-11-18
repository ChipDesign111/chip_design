# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 200B; remaining SRAM 7672B.

Task segment 0: base 0x80001ec0, COUNT=1

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 16/8/1 | 0x80001fb0 | 0x80001f08 | 0x80001fa8 | NONE | 1/1/0 | 0 |

