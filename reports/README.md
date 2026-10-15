# Verification evidence

Reports identify the inputs, source hashes, commands, results and limits of a particular baseline. They are historical evidence, not an assertion that every subsequent revision was retested identically.

## Engineering workflows

[sram-integration.md](sram-integration.md) / [sram-integration.json](sram-integration.json): selectable CPU SRAM, local vendor model, full SoC across three backends and public clean-checkout reproduction. Functional simulation is distinguished from physical timing signoff.

[engineering-workflows.md](engineering-workflows.md) / [engineering-workflows.json](engineering-workflows.json): portable entry point, repository policy, layered CI definition, local full regression and clean-checkout reproduction. Hardware and model remain identical to the functional baseline below.

## Current functional baseline

- [real-model.md](real-model.md) / [real-model.json](real-model.json): trained model on all 2947 official test rows; 5894 RTL inferences; 24 real CPU inputs; synthetic, original-platform and generic-structure regression.
- Integrated source baseline: `fb301c3d6f04041603c82d432d3772f69b69458b`. The report records normalized source SHA values for the tested implementation.

A later documentation or tooling change may alter source fingerprints without changing the validated RTL. New functional claims require new evidence; historical JSON is not silently regenerated.

## Historical baselines

- [baseline.md](history/baseline.md) / [baseline.json](history/baseline.json): single-MAC implementation and original platform verification.
- [tiled-v2.md](history/tiled-v2.md) / [tiled-v2.json](history/tiled-v2.json): tiled synthetic regression, cycle comparison and generic structure.

## Scope

Measured values are simulation cycles and model accuracy. No report establishes target frequency, power, mapped SRAM/BRAM cost, FPGA success or ASIC signoff.

Generated waveforms/databases and runtime logs remain in ignored build/; CI retains selected open-tool logs and result summaries. Release evidence requirements: [release process](../docs/releases.md).
