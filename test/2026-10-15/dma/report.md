# DMA real-model validation

Date: 2026-10-15. Source base: `6f3f1e033431d2f934f427a622987fa241730bb5`.
Exact tested source identity: [source_manifest.json](source_manifest.json). Metrics, tools, firmware SHA and regression outcomes: [results.json](results.json).

## Matched workload

Both RV32I images run on the same DMA-enabled SoC. They use the same supplied 64→32→6 model and 24 real UCI inputs (four per class), 12 paired commands, unchanged integer rules and identical hidden/score/class verification. Only the loading implementation differs. Copy 598 parameter words (weights + biases) once and 384 input words across 24 inputs. Quantization settings and result reads remain CPU-controlled.

The portable SRAM and the locally licensed RA1SHD model produced identical cycle measurements. Vendor timing checks are explicitly disabled for functional simulation; no vendor source or physical view is published.

| Measured interval | CPU copy cycles | DMA cycles | Speedup |
| --- | ---: | ---: | ---: |
| Parameter loading, including setup/polling | 29330 | 1872 | 15.67× |
| Cumulative input loading | 19656 | 6960 | 2.82× |
| Total measured loading | 48986 | 8832 | 5.55× |
| Application, including identical result checks | 76496 | 36342 | 2.10× |
| Warm inference/check segment after parameters are loaded | 47067 | 34371 | 1.37× |
| Entire SoC execution, including boot/status stores | 76725 | 36571 | 2.10× |

The firmware reads mcycle with counters explicitly enabled. Input and parameter timers include software descriptor/setup, polling and completion validation. The warm timer begins after model/quantization/batch setup, covering input loading, inference, result verification and acknowledgement. Total SoC cycles are measured independently by the testbench from CPU reset release to its real completion write. Hex preload before CPU reset release is excluded in both modes. These numbers include verification overhead and are not a bare inference production benchmark.

Non-transfer application work is exactly 27510 cycles in both programs, independently confirming that the measured gain comes from transport.

The testbench observes 982 DMA read beats and 982 write beats, with 62 read bursts and 62 write bursts. The CPU baseline has zero DMA traffic. NPU internal single/batch/overlap assertions remain 39/59/18; the gain is transport-related. The fixture has 18/24 correct activity labels; all 24 hardware outputs agree with integer gold, including model misclassifications.

## Implementation and regression

- AXI DMA: at most 16-word bursts, 512-bit FIFO, one outstanding burst, independent AW/W handshakes, 4 KiB boundary splitting and response/RLAST checks.
- Protocol tests: 227 completed cases including 200 random copies with random channel stalls, tail lengths, bounds rejection, NPU-busy rejection, errors, conflicting writes and four reset phases. A separate ingress test checks tagged DMA writes and blocked host writes.
- A clean checkout without licensed files, in a path containing spaces, reproduced the full CPU/DMA benchmark with identical cycle metrics, repository checks and all generic synthesis checks; tracked files remained clean.
- Complete local CI: 1000 synthetic cases / 3000 core inferences, 12 MMIO cases, SRAM unit tests, 24 real rows / 48 RTL inferences and generic structure checks passed.
- Existing non-DMA eight-/six-inference CPU programs and original 24-input model program passed on the licensed SRAM model. The original real-model image remains byte-identical (6232 bytes used).
- DMA engine generic synthesis: 64 B FIFO + 343 explicit register bits, no multipliers or latches. This excludes the additional AXI initiator/routing and target mapping.
- NPU math, tiling and weight banks unchanged. Two SoC integration files intentionally add DMA/CSR routing; rtl/manifest.json records their previous SHA and migration reason. CPU/AXI/debug/clock/boot sources remain unchanged.

```sh
python tools/project.py test --suite dma-unit
python tools/project.py test --suite dma --memory portable-sram --vsim /path/to/vsim
python tools/project.py test --suite dma --memory ra1shd --vsim /path/to/vsim
python tools/project.py ci
```

Source snapshots and local detailed logs are recorded in each ignored test run. Public evidence excludes licensed-model compile logs/databases. Public CI independently runs DMA unit tests and generic synthesis without vendor views. Register semantics, integration boundaries and limitations: [DMA design](../../../report/dma.md).

## Limits

No compute/loading overlap, infinite queue, result DMA, interrupt, hardware timeout or physical timing/area/power claim. The full 2947-row test was not repeated here. The 2.10× result includes one parameter load plus 24 inputs; weight-reuse workloads should use the measured 1.37× warm result rather than extrapolate the cold result indefinitely.
