# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 200B; remaining SRAM 6072B.

Task segment 0: base 0x80001880, COUNT=2

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 48/24/2 | 0x80001f60 | 0x80001a10 | internal | RELU | 1/1/1 | 0 |
| 1 | FC | 24/8/2 | internal | 0x80001930 | 0x80001ef0 | NONE | 1/1/0 | 131072 |

