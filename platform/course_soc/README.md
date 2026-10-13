# Fixed SoC baseline

Source snapshot: provided Lab 3 SoC_cv32e40p package with four-port NPU integration. This identifies the selected reference snapshot and does not assert an untouched upstream release.

Includes CPU, AXI, debug, clock/reset, boot storage, 8 KiB SRAM, my_soc_top and my_npu_subsystem. Original TB/C/hex, startup/linker and source list are retained under verification/lab3, sw/startup/lab3 and filelists.

[manifest.json](manifest.json) records source-relative paths and byte-level SHA-256 for all 90 fixed files. Original copyright/license headers and line endings are preserved.

The original NPU is not part of the frozen perimeter: project implementations reside in rtl/npu/har and rtl/npu/lab3. See [provenance](../../docs/provenance.md) and [third-party notices](../../THIRD_PARTY_NOTICES.md).
