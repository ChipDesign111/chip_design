# Memory adapters

Reserved boundary for target-specific storage implementations; no independent module is compiled from this directory.

Current weights use har_weight_store in rtl/npu/har. A new adapter must preserve read latency, reset validity, loading and busy-write semantics, and enter both unit and SoC source lists. See [memory budget](../../docs/memory-budget.md) and [development guide](../../docs/change-guide.md).
