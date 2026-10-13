# Driver boundary

A production C driver is not yet implemented. Current CPU validation uses looped RV32I self-check programs generated from scripts.

A driver must provide aligned parameter/input loading, timeout-bounded polling, result access and completion acknowledgement, matching [MMIO](../../docs/mmio.md).
