# FPGA firmware batch results

Environment: OpenOCD Tcl 127.0.0.1:6666

Status: **PASS**; PASS 62, FAIL/ERROR 0, remaining 0.

Full SoC cycles: first non-debug fetch after commit through PASS/FAIL; includes firmware checks.
NPU/DMA counters are for the **last hardware task**, not a whole-network sum.

| Image | Result | Words checked | Full SoC cycles | Last NPU cycles | DMA/MAC read / write / total |
|---|---|---:|---:|---:|---|
| int8_random_00_batch4 | PASS | 60 | 2745 | 962 | 466 / 499 / 500 |
| int8_random_01_batch2 | PASS | 30 | 1981 | 850 | 269 / 268 / 269 |
| int8_random_02_batch1 | PASS | 15 | 1602 | 801 | 133 / 132 / 133 |
| int8_random_03_batch2 | PASS | 30 | 1962 | 851 | 269 / 268 / 269 |
| int8_random_04_batch1 | PASS | 15 | 1608 | 805 | 133 / 132 / 133 |
| int8_random_05_batch2 | PASS | 30 | 1981 | 850 | 269 / 268 / 269 |
| int8_random_06_batch4 | PASS | 60 | 2700 | 952 | 466 / 499 / 500 |
| int8_random_07_batch2 | PASS | 30 | 1962 | 851 | 269 / 268 / 269 |
| int8_random_08_batch1 | PASS | 15 | 1608 | 805 | 133 / 132 / 133 |
| int8_random_09_batch2 | PASS | 30 | 1981 | 850 | 269 / 268 / 269 |
| int8_random_10_batch1 | PASS | 15 | 1602 | 801 | 133 / 132 / 133 |
| int8_random_11_batch2 | PASS | 30 | 1962 | 851 | 269 / 268 / 269 |
| int8_random_12_batch4 | PASS | 60 | 2745 | 962 | 466 / 499 / 500 |
| int8_random_13_batch2 | PASS | 30 | 1981 | 850 | 269 / 268 / 269 |
| int8_random_14_batch1 | PASS | 15 | 1602 | 801 | 133 / 132 / 133 |
| int8_random_15_batch2 | PASS | 30 | 1962 | 851 | 269 / 268 / 269 |
| int8_random_16_batch1 | PASS | 15 | 1608 | 805 | 133 / 132 / 133 |
| int8_random_17_batch2 | PASS | 30 | 1981 | 850 | 269 / 268 / 269 |
| int8_random_18_batch4 | PASS | 60 | 2700 | 952 | 466 / 499 / 500 |
| int8_random_19_batch2 | PASS | 30 | 1962 | 851 | 269 / 268 / 269 |
| int8_random_20_batch1 | PASS | 15 | 1608 | 805 | 133 / 132 / 133 |
| int8_random_21_batch2 | PASS | 30 | 1981 | 850 | 269 / 268 / 269 |
| int8_random_22_batch1 | PASS | 15 | 1602 | 801 | 133 / 132 / 133 |
| int8_random_23_batch2 | PASS | 30 | 1962 | 851 | 269 / 268 / 269 |
| int8_random_24_batch4 | PASS | 60 | 2745 | 962 | 466 / 499 / 500 |
| int8_random_25_batch2 | PASS | 30 | 1981 | 850 | 269 / 268 / 269 |
| int8_random_26_batch1 | PASS | 15 | 1602 | 801 | 133 / 132 / 133 |
| int8_random_27_batch2 | PASS | 30 | 1962 | 851 | 269 / 268 / 269 |
| int8_random_28_batch1 | PASS | 15 | 1608 | 805 | 133 / 132 / 133 |
| int8_random_29_batch2 | PASS | 30 | 1981 | 850 | 269 / 268 / 269 |
| int8_random_30_batch4 | PASS | 60 | 2700 | 952 | 466 / 499 / 500 |
| int8_random_31_batch2 | PASS | 30 | 1962 | 851 | 269 / 268 / 269 |
| int8_uci_00_batch4 | PASS | 60 | 2700 | 952 | 466 / 499 / 500 |
| int8_uci_01_batch4 | PASS | 60 | 2700 | 952 | 466 / 499 / 500 |
| int8_uci_02_batch4 | PASS | 60 | 2700 | 952 | 466 / 499 / 500 |
| int8_uci_03_batch4 | PASS | 60 | 2700 | 952 | 466 / 499 / 500 |
| int8_uci_04_batch4 | PASS | 60 | 2700 | 952 | 466 / 499 / 500 |
| int8_uci_05_batch4 | PASS | 60 | 2700 | 952 | 466 / 499 / 500 |
| har_b1_cpu | PASS | 15 | 51945 | 0 | 0 / 0 / 0 |
| har_b1_npu | PASS | 15 | 1792 | 805 | 133 / 132 / 133 |
| har_b2_cpu | PASS | 30 | 76675 | 0 | 0 / 0 / 0 |
| har_b2_npu | PASS | 30 | 2337 | 857 | 269 / 268 / 269 |
| har_b3_cpu | PASS | 45 | 129000 | 0 | 0 / 0 / 0 |
| har_b3_npu | PASS | 45 | 2856 | 898 | 401 / 402 / 403 |
| har_b4_cpu | PASS | 60 | 154660 | 0 | 0 / 0 / 0 |
| har_b4_npu | PASS | 60 | 3370 | 952 | 466 / 499 / 500 |
| raw_full_b1_cpu | PASS | 24 | 36996 | 0 | 0 / 0 / 0 |
| raw_full_b1_raw | PASS | 24 | 3969 | 713 | 124 / 124 / 124 |
| raw_full_b2_cpu | PASS | 48 | 77724 | 0 | 0 / 0 / 0 |
| raw_full_b2_raw | PASS | 48 | 6775 | 722 | 248 / 248 / 248 |
| raw_full_b3_cpu | PASS | 72 | 116264 | 0 | 0 / 0 / 0 |
| raw_full_b3_raw | PASS | 72 | 9568 | 726 | 372 / 372 / 372 |
| raw_full_b4_cpu | PASS | 96 | 180229 | 0 | 0 / 0 / 0 |
| raw_full_b4_raw | PASS | 96 | 12349 | 730 | 434 / 465 / 465 |
| raw_tail_b4_cpu | PASS | 104 | 187168 | 0 | 0 / 0 / 0 |
| raw_tail_b4_raw | PASS | 104 | 26361 | 730 | 434 / 465 / 465 |
| raw_k_split_b4_cpu | PASS | 160 | 254107 | 0 | 0 / 0 / 0 |
| raw_k_split_b4_raw | PASS | 160 | 19256 | 730 | 434 / 465 / 465 |
| raw_multi_b2_cpu | PASS | 128 | 189366 | 0 | 0 / 0 / 0 |
| raw_multi_b2_raw | PASS | 128 | 83497 | 717 | 248 / 248 / 248 |
| raw_wide_b3_cpu | PASS | 120 | 186747 | 0 | 0 / 0 / 0 |
| raw_wide_b3_raw | PASS | 120 | 14947 | 726 | 372 / 372 / 372 |

## Paired full SoC speedups

| Pair | CPU cycles | NPU cycles | CPU / NPU |
|---|---:|---:|---:|
| har_b1 | 51945 | 1792 | 28.9872x |
| har_b2 | 76675 | 2337 | 32.8092x |
| har_b3 | 129000 | 2856 | 45.1681x |
| har_b4 | 154660 | 3370 | 45.8932x |
| raw_full_b1 | 36996 | 3969 | 9.3212x |
| raw_full_b2 | 77724 | 6775 | 11.4722x |
| raw_full_b3 | 116264 | 9568 | 12.1513x |
| raw_full_b4 | 180229 | 12349 | 14.5946x |
| raw_tail_b4 | 187168 | 26361 | 7.1002x |
| raw_k_split_b4 | 254107 | 19256 | 13.1963x |
| raw_multi_b2 | 189366 | 83497 | 2.2679x |
| raw_wide_b3 | 186747 | 14947 | 12.4939x |
