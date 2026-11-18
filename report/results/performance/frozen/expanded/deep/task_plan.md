# SoC execution plan

INT8 zero-point0; exact rounding/saturation boundaries follow task ABI v1.
Code 200B; remaining SRAM 6584B.

Task segment 0: base 0x80001a80, COUNT=3

| Task | OP | K/N/B | Input | Weights | Output | ACT | INIT/LAST/KEEP | Context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | FC | 17/13/2 | 0x80001f98 | 0x80001db4 | internal | LEAKY_RELU | 1/1/1 | 0 |
| 1 | FC | 13/9/2 | internal | 0x80001cb0 | internal | RELU6 | 1/1/1 | 131072 |
| 2 | FC | 9/5/2 | internal | 0x80001c4c | 0x80001f08 | TANH | 1/1/0 | 262144 |

