# 2026-10-15 tests

- scripts/：当前 NPU、MMIO、模型、SRAM、完整 SoC、固件和通用综合脚本。
- rtl/：当前 testbench；tb_soc 在复位期间通过存储端口装载程序，被动观察 CPU 完成写。
- fixtures/：带来源、行号和 SHA 的六类 24 条真实输入。
- sram-integration/：目录重组之前的 SRAM 验证记录，保留原 SHA/路径语境。
- layout-migration/：本次目录重组后的实际验证证据。
- runs/：每次运行的独立时间戳产物，默认忽略。

运行入口：python tools/project.py test。验证范围和依赖见 [开发说明](../../report/development.md)。
