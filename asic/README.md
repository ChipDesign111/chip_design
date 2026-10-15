# ASIC target integration

Not implemented: no technology mapping, target timing constraints, physical flow or signoff result is included.

A target flow requires authorized libraries/macros, synthesis, floorplan/power, placement, CTS, routing, STA and physical checks. Restricted technology data remains outside the repository; distributable scripts and summarized evidence must identify their source revision and constraints.

Generic Yosys checks are technology-independent and are not ASIC signoff.

## Local SRAM dependency

Licensed physical-IP views live under ignored asic/vendor/. Public sources include only a project-owned interface declaration and adapter. No vendor timing/layout views are needed by CI. See [SRAM integration](../docs/sram.md).
