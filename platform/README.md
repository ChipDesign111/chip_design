# Reference platform

[course_soc/](course_soc/README.md) holds the fixed CV32E40P/AXI/debug/boot/SRAM integration. Accelerator implementations are maintained separately in rtl/npu.

The platform and original regression inputs are protected by a 90-file SHA-256 manifest. Normal accelerator development does not modify these files. Baseline updates require provenance, an explicit diff and complete SoC regression.

Run `python project.py check`. See [provenance](../docs/provenance.md), [component notices](../THIRD_PARTY_NOTICES.md) and [architecture](../docs/architecture.md).
