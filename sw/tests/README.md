# Software test boundary

Generated CPU self-checks currently live under build/, with their source generators in scripts. No standalone C test build is implemented here.

Future C tests must compare complete numerical results, fit the 8 KiB SRAM budget and be executed in the real CPU/SoC test path.
