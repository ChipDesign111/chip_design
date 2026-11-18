# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 200B; remaining SRAM 5176B.

Task segment 0: base 0x80001500, COUNT=2

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 64/32/1 | 0x80001f80 | 0x800016b8 | internal | RELU | 1/1/1 | 0 |
| 1 | FC | 32/6/1 | internal | 0x800015a0 | 0x80001f38 | NONE | 1/1/0 | 131072 |

