> 历史测试记录：保留当时的结果和路径语境，不能作为当前目录布局的运行说明。对应脚本可从报告所记录的 Git revision 获取。

# Engineering workflow validation

Date: 2026-10-13. Source base: `fb301c3d6f04041603c82d432d3772f69b69458b`.
Tested entry point, policy checker, workflow and dependency SHA values are recorded in [engineering-workflows.json](results.json).

This change reorganizes project documentation and adds the portable `project.py` entry point and four independent CI jobs. Accelerator RTL, model parameters, firmware/fixtures and all 90 frozen platform files retain their Git blob identities. Historical JSON reports retain their blob identities after relocation.

| Command / check | Local result |
| --- | --- |
| `python project.py ci` | Repository policy, frozen inputs, 1000 synthetic cases / 3000 core inferences, 12 MMIO cases, 24 real rows / 48 RTL inferences and generic synthesis passed |
| `python project.py test --suite soc --vsim <local-tool>` | Four original images and two tiled self-test images passed |
| `python project.py test --suite model-soc --vsim <local-tool>` | 24 real CPU inputs in 12 batches passed, 76249 SoC cycles |
| Clean checkout in a path containing spaces | check, unit with 12 cases, real model and synthesis passed without a preexisting build/data directory; tracked files remained clean |
| CLI failure paths | Invalid count, data root and explicit tool returned 2; required missing NumPy returned 1; check from another working directory returned 0 |

Tools: Python 3.12.14, NumPy 2.3.5, Icarus 11, ModelSim 2019.2 and Yosys 0.18+29. Runtime log paths and per-stage outcomes are in the JSON. Local tool/license paths are not part of the portable configuration. GitHub CI records its Linux results on the associated pull request.

The 24-row fixture measures implementation agreement, not overall classification accuracy. The earlier full 2947-row test remains a separate [model baseline](../real-model/report.md); it was not rerun for this documentation/tooling change. FPGA, target memory mapping, timing, power, area and ASIC signoff remain outside this evidence.
