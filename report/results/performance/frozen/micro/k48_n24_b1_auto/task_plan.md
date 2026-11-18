# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 200B; remaining SRAM 6520B.

Task segment 0: base 0x80001a40, COUNT=1

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 48/24/1 | 0x80001f90 | 0x80001a98 | 0x80001f78 | NONE | 1/1/0 | 0 |

