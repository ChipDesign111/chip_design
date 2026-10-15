# Memory adapters

Project-owned single-port CPU SRAM adapter with portable-sram and local ra1shd backends. The original reference memory remains the default.

Current weights use har_weight_store in rtl/npu/har. A new adapter must preserve read latency, reset validity, loading and busy-write semantics, and enter both unit and SoC source lists. See [memory budget](../../docs/memory-budget.md) and [development guide](../../docs/change-guide.md).

Implementation, backend selection and verification: [SRAM integration](../../docs/sram.md).
