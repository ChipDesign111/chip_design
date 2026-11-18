# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 200B; remaining SRAM 7352B.

Task segment 0: base 0x80001d80, COUNT=1

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | ACTIVATION | 0/32/4 | 0x80001f40 | 0x00000000 | 0x80001ec0 | SIGMOID | 0/1/0 | 0 |

