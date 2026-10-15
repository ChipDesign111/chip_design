# Source manifests

lab3_original.f is an immutable source reference. scripts/run_tests.py expands its platform paths and selects the lab3 or har accelerator, producing build/lab3.f and build/har.f.

The HAR_RTL list is shared by unit, model and synthesis backends; SoC profile source selection is explicit. A new module must enter both paths. Do not edit generated lists or compile both simple_npu_top implementations.

--memory portable-sram / ra1shd selects a replacement main-memory implementation and independent SRAM TB while retaining the frozen source list. The generated list compiles exactly one my_mainmem. See [SRAM](../docs/sram.md).
