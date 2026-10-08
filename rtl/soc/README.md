# SoC 集成

计划实现项目顶层、NPU 子系统包装和 MMIO。复用 platform 中共同底座，采用明确编译清单。
以 [MMIO 草案](../../docs/mmio.md) 评审接口，核对 axi2mem 读下一拍契约和 byte/word 地址。
