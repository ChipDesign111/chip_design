# Workflow backends

Use [project.py](../project.py) as the supported command entry point; existing scripts remain directly callable.

| Backend | Responsibility |
| --- | --- |
| check_repo.py / check_platform.py | Repository policy and frozen-input integrity |
| run_tests.py | Icarus unit/MMIO and ModelSim CPU regressions |
| generate_vectors.py | Deterministic synthetic gold |
| run_model_tests.py / export_real_model.py | Trained-model reference, real-input RTL and CPU tests |
| build_har_firmware.py / build_model_firmware.py | Reproducible RV32I self-check images |
| check_synthesis.py | Generic Yosys memory/logic checks |
| download_uci_har.py | Official test-data acquisition |
| import_lab3.py | Controlled baseline import, not normal development |

Backends locate the repository root and write ignored build/ artifacts. Tool paths are supplied through PATH/CLI; secrets and machine-specific configuration are not source inputs. Commands and artifact locations: [environment](../docs/environment.md).
