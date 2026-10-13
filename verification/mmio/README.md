# MMIO and trained-model regression

[tb_har_mmio.sv](tb_har_mmio.sv) verifies packing, synchronous readback, status, invalid configuration, busy-write rejection, reset and paired execution.

[tb_har_model.sv](tb_har_model.sv) loads trained parameters once and checks every intermediate/output value for real inputs in single and paired modes. Classification accuracy is counted separately from hardware/reference agreement.

Run `python project.py test --suite unit` and `python project.py test --suite model`. The latter uses 24 committed real fixtures unless an official dataset root is supplied.
