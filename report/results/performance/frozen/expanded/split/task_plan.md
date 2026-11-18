# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 200B; remaining SRAM 3384B.

Task segment 0: base 0x80000e00, COUNT=5

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 64/32/1 | 0x80001f7c | 0x80001214 | 0x00000000 | NONE | 1/0/0 | 0 |
| 1 | FC | 1/32/1 | 0x80001fbc | 0x80001a14 | 0x80001f24 | RELU | 0/1/0 | 0 |
| 2 | FC | 64/9/1 | 0x80001f7c | 0x80001a54 | 0x00000000 | NONE | 1/0/0 | 32 |
| 3 | FC | 1/9/1 | 0x80001fbc | 0x80001e54 | 0x80001f44 | RELU | 0/1/0 | 32 |
| 4 | FC | 41/9/1 | 0x80001f24 | 0x80000f50 | 0x80001f18 | NONE | 1/1/0 | 131072 |

