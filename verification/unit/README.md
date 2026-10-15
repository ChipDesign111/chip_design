# Operator test boundary

No standalone operator testbench is currently compiled from this directory. Arithmetic boundary coverage is supplied by tb_har_core and the independent integer reference.

Extracted operators should gain focused tests here while preserving full-network and SoC regression.

tb_mainmem_sram exercises all 2048 words, every byte mask, disabled writes, read gating, synchronous sampling and data retention across reset. Run project.py test --suite memory; use --memory ra1shd for the locally licensed model. See [SRAM](../../docs/sram.md).
