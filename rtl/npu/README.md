# Neural accelerator

| Profile | Implementation |
| --- | --- |
| `har` | Two FC1 16×4 tiles, one FC2 6×2 tile, synchronous banked weights, hidden double buffering |
| `lab3` | Unsigned 4-bit 4×4 compatibility accelerator |

Both profiles provide the fixed simple_npu_top interface. HAR supports one or two inputs per command: 39 / 59 core cycles, with 18 cycles of cross-input stage overlap.

[har_dot_tile.sv](har/har_dot_tile.sv) implements registered products and output-stationary accumulation. [har_weight_store.sv](har/har_weight_store.sv) implements 38 synchronous banks. [har_npu_core.sv](har/har_npu_core.sv) schedules the pipeline; [simple_npu_top.sv](har/simple_npu_top.sv) implements MMIO.

Contracts: [numerics](../../docs/numerics.md), [MMIO](../../docs/mmio.md). Architecture: [tiled NPU](../../docs/tiled-npu.md). Evidence: [reports](../../reports/README.md). Target timing/area and physical implementation are not established by simulation.
