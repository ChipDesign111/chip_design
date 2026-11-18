# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 200B; remaining SRAM 7096B.

Task segment 0: base 0x80001c80, COUNT=2

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 9/32/1 | 0x80001fb4 | 0x80001d04 | 0x80001f88 | NONE | 1/1/0 | 0 |
| 1 | FC | 9/9/1 | 0x80001fb4 | 0x80001e44 | 0x80001fa8 | NONE | 1/1/0 | 32 |

