# 历史固件身份记录

此目录保留 2026-11-01 固件的 [image_manifest.json](image_manifest.json) 和 [DMA 配置](firmware_dma.json)，原字节与 SHA 不变。完整镜像已迁至本机外部工作区 `archives/20261101_rtl-fce9d9b_board-pass/firmware/`，不再跟踪生成的 hex/bin。

当时镜像为 2048×32-bit（8 KiB），包含 RV32I 自检程序、权重、输入、整数 golden 和 PASS/FAIL 回写。集合为 32 个随机/边界镜像、6 个 UCI 四样本镜像，以及 canonical 别名。原 canonical hex SHA-256 为 `fa38f91311768cd73386f8e093370831383d9e0e1b8a4832a2f3f978a2bfe850`。

这是 INT32/旧 FC2 调度的冻结记录，不能由当前生成器重建为同一历史镜像。新机器生成当前固件请使用[当前操作方法](../../../README.md)，历史验证结论见[版本报告](../TEST_REPORT.md)。
