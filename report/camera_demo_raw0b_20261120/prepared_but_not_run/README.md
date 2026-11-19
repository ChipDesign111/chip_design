# Prepared inputs — physical tests NOT_RUN

These are replay inputs, independent expected tensors and a synthetic engineering-model resident image. They contain no FPGA-returned results. CPU JTAG currently returns all zeros; neither 100 arithmetic requests nor 12 trained engineering requests has run on the board.

Arithmetic: four known vectors repeated 25 times; use resident package ../soc. Camera: 12 held-out session feature rows, use camera/resident, floating input quantized by the host. See camera/provenance.json for sample selection, exact package reconstruction and reference identity. No human action accuracy claim.

Reprogram the empty-SRAM bitstream between loading different packages. Commands and test boundaries are in the parent README.
