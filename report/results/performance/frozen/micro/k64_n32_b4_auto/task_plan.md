# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 200B; remaining SRAM 5304B.

Task segment 0: base 0x80001580, COUNT=1

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 64/32/4 | 0x80001ec0 | 0x800015c0 | 0x80001e40 | NONE | 1/1/0 | 0 |

