> 历史测试记录：保留当时的结果和路径语境，不能作为当前目录布局的运行说明。对应脚本可从报告所记录的 Git revision 获取。

# SRAM integration validation

Date: 2026-10-15. Source base: `dec1a66dd394ba1a0626a092e736bb1afcaade72`.
Exact tested project-source SHA values, tool versions and per-test outcomes are in [sram-integration.json](results.json).

The supplied nine files were moved intact to ignored asic/vendor/RA1SHD_2048x32M8; the local inventory records original SHA-256 values. Public changes contain project-owned adapters/tests and an interface-only blackbox, not vendor implementation/timing/layout views. NPU RTL, model parameters, firmware/fixtures, and all 90 frozen platform files remain unchanged.

| Verification | Result |
| --- | --- |
| Portable and local vendor memory unit tests | Each passed 6128 read comparisons / 4064 writes; all 2048 addresses, all 16 byte masks, disabled writes, read enable semantics, synchronous output and reset retention |
| reference, portable-sram and ra1shd SoC | Each passed four original CPU images plus tiled eight-/six-inference self-tests |
| All three memory backends, trained model SoC | Each passed 24 real inputs / 12 batches, comparing hidden/score/class with integer reference |
| NPU regression via project.py ci | 1000 synthetic parameter cases / 3000 core inferences, 12 MMIO cases, 24 real rows / 48 RTL inferences passed |
| Generic Yosys | NPU structure unchanged; portable main RAM 65536 bits / one synchronous read port; macro backend one blackbox, no latches |
| Clean checkout without licensed files | check, memory, model, synth and invocation from another directory passed in a path with spaces |
| Failure-path checks | Missing vendor model returned 2; a synthetic forced tracked entry under asic/vendor caused repository check to return 1 |

The new SoC TB detects CPU completion writes after the sampling edge; the original TB polls stored status on the next edge. New-backend counts are consistently one lower (trained model 76248 vs original 76249). This is monitor accounting, not a memory/CPU performance improvement. Firmware and NPU internal 39 / 59 / 18 cycle assertions remain unchanged. The 24-row fixture has 18 correct activity labels; hardware agreement is checked independently of those model errors.

Initial vendor SoC execution with timing checks enabled failed: zero-delay RTL input transitions triggered model hold notifiers and the CPU timed out. Functional runs explicitly use ModelSim +notimingchecks; Icarus unit runs do not enable specify checks. No timing error is relabeled as a timing pass, no artificial RTL delays were added, and no vendor source was edited. STA/SDF and target clock signoff remain separate work.

The simulation loader writes firmware through SRAM ports while CPU reset is asserted and never injects PASS or accesses vendor internal storage. A hardware download/boot path remains required for deployment. No Liberty/CDL/layout processing, mapped area/power, physical verification, FPGA success or ASIC signoff is claimed. Full 2947-row model evidence remains the earlier model baseline; this change uses the committed 24-row fixture.
