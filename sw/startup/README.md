# Startup baseline

lab3/ contains immutable source startup/linker material recorded by the platform manifest. It is retained for compatibility and future compiler integration.

Current RV32I generators emit self-contained programs without a C runtime or function-call stack. A GCC-based build must explicitly validate startup, memory layout, stack and magic-region placement.
