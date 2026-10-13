# Accelerator RTL

[npu/](npu/README.md) contains the implemented accelerators. `har/` is the INT8 MLP implementation; `lab3/` is the isolated legacy compatibility profile. Only one simple_npu_top is compiled at a time.

The system top and AXI bridge remain in [platform](../platform/README.md). `memory/` and `soc/` reserve future component boundaries and currently contribute no RTL to a build.

See [architecture](../docs/architecture.md), [development](../docs/change-guide.md), and [verification](../docs/verification.md).
