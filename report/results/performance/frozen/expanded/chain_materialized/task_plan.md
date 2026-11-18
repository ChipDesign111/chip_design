# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 200B; remaining SRAM 6008B.

Task segment 0: base 0x80001840, COUNT=3

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 48/24/2 | 0x80001f60 | 0x80001a10 | 0x80001f30 | NONE | 1/1/0 | 0 |
| 1 | ACTIVATION | 0/24/2 | 0x80001f30 | 0x00000000 | 0x80001f00 | RELU | 0/1/0 | 0 |
| 2 | FC | 24/8/2 | 0x80001f00 | 0x80001930 | 0x80001ef0 | NONE | 1/1/0 | 131072 |

