# Machine-readable specification

[project.json](project.json) defines network dimensions, numerical widths, tile configuration, cycle contract and MMIO windows. Repository checks validate its schema and aperture layout.

Runtime tool selection uses project.py flags or PATH; ModelSim licensing uses the local environment. No machine-specific paths or credentials are part of this specification. Historical environment templates are retained only in docs/archive.
