# Seven-directory layout validation

Date: 2026-10-15. Base: 761a72d88c5c819b7b01cdb2269426e05d96a0df.

Top-level source directories are rtl, fpga, model, eda, test, report and tools. FPGA/EDA contain only Git placeholders. Full SoC RTL is under rtl; only the current HAR NPU is built. Original NPU, its 4x4 fixtures, importer, source list, startup material and reference SRAM implementation were removed. Retained perimeter: 75 files preserve original byte SHA and copyright; NPU/model parameters and historical result JSON preserve Git blob identity.

Current scripts: [scripts](../scripts/run_tests.py); exact tested source identity: [source-manifest.json](source-manifest.json); commands, outcomes and clean-checkout evidence: [results.json](results.json). Each invocation additionally retains its own timestamped script/TB/tools snapshots, logs, results and report in the ignored runs directory. Public CI archives permitted evidence as artifacts.

| Verification | Result |
| --- | --- |
| Full synthetic regression | 1000 cases, 3000 core inferences and 12 MMIO cases passed |
| Full trained model | 2947 actual UCI inputs, 5894 single/paired RTL inferences; every hidden/score/class matches integer reference |
| Supplied SRAM model + real CPU | 24 real inputs in 12 batches passed via CV32E40P/AXI/NPU; 76248 monitor cycles |
| Portable SoC | Current eight-/six-inference self-test programs passed |
| Memory unit | Portable and local vendor model each passed 6128 reads / 4064 writes, all words and byte masks |
| Generic structure | NPU 38 banks / 76 sync ports / 172 multipliers unchanged; main RAM 65536 bits / one sync read port; macro connectivity one blackbox |
| Clean checkout without licensed views, path with spaces | check, unit12, memory, model, synth and 24-input complete SoC passed |
| Negative / portability | Missing licensed model and removed reference profile rejected; tracked tools/local rejected; cross-directory invocation passed |

Integer classification accuracy remains 2504/2947 = 84.9678%; the 24-row CPU fixture has 18 correct labels. Correct RTL agreement does not imply every activity prediction is correct. The supplied checkpoint was selected using its original test split, so this is reproduction rather than a fresh independent blind test.

Nine licensed files were moved intact into ignored tools/local/vendor. No licensed implementation or physical view is distributed. Vendor SoC uses +notimingchecks for functional simulation. Timing, STA/SDF, target memory mapping/PPA, FPGA and ASIC signoff are not claimed. Firmware loading remains a testbench port operation during CPU reset.
