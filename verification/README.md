# Verification

Verification is layered into scalar/vector integer references, RTL control/arithmetic, MMIO, full CPU/SoC and technology-independent synthesis checks.

| Location | Scope |
| --- | --- |
| [npu/](npu/README.md) | Synthetic parameter and pipeline regression |
| [mmio/](mmio/README.md) | Interface and trained-model tests |
| [vectors/](vectors/README.md) | Small reproducible real-input fixtures |
| lab3/ | Immutable imported tests and CPU images |
| [soc/](soc/README.md) | SoC integration boundary |
| [unit/](unit/README.md) | Future independent operator tests |

Run `python project.py test --suite unit` and `--suite model`; complete CPU verification uses `--suite soc` and `--suite model-soc` with ModelSim. Definitions and pass conditions: [verification strategy](../docs/verification.md).
