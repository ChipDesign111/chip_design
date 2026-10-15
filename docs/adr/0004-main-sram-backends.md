# ADR 0004: Selectable main SRAM backend

Status: Accepted

## Context

The supplied 2048×32 single-port SRAM matches the 8192-byte CPU main memory. Its licensed implementation/physical views are local dependencies. The NPU weight banks have different port and bandwidth requirements.

## Decision

Keep the 90-file imported platform and original fixtures immutable. Extend ADR 0001 with an explicit compile-time overlay: replace my_mainmem and the SoC test top in the generated source list. Preserve CPU address mapping, byte enables and synchronous read latency. Keep reference as the default; offer portable-sram and local ra1shd backends through the same project-owned adapter. Do not compile duplicate module definitions.

Preload simulation firmware through memory ports while CPU reset is asserted. Monitor actual CPU writes for completion, independently of vendor array names. The macro has no hardware initialization or reset clear. Vendor SoC runs are functional with timing checks explicitly disabled; timing signoff requires a separate mapped/annotated flow.

## Consequences

Public CI remains reproducible without licensed views. Source checks reject tracked asic/vendor files. CPU images and NPU numeric/cycle contracts remain unchanged. Target constraints, corners, power, placement, physical views and a hardware program loader remain integration work. No direct mapping of the 38 weight banks to one single-port macro is claimed. See [SRAM integration](../sram.md).
