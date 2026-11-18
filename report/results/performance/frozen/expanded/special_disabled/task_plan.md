# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 200B; remaining SRAM 4792B.

Task segment 0: base 0x80001380, COUNT=2

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 64/32/4 | 0x80001ec0 | 0x80001520 | internal | RELU | 1/1/1 | 0 |
| 1 | FC | 32/6/4 | internal | 0x80001408 | 0x80001da0 | NONE | 1/1/0 | 131072 |

