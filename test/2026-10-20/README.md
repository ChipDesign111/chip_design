# 最终 W8A4 测试

| 脚本 | 覆盖 |
| --- | --- |
| scripts/run_stream_tests.py | 24条真实模型逐值检查、248项DMA协议、包异常/顺序/复位；可选全2947条 |
| scripts/run_soc_tests.py | 唯一最终设计的CPU/AXI/SRAM/DMA/NPU自检，24条真实输入 |
| scripts/run_sram_tests.py | 主存全地址、掩码、随机和复位，支持两种后端 |
| scripts/check_stream_synthesis.py | 最终NPU/DMA通用结构 |
| scripts/check_sram_synthesis.py | 主存行为推断及宏端口连接 |

固定输入与金标准在 [fixtures/w8a4_soc24.json](fixtures/w8a4_soc24.json)。精简证据见 [validation.json](validation.json)。从根目录使用 `python tools/project.py test --suite unit|memory|soc|all`，实际选其中一个suite。SoC需 `--vsim`，授权模型需 `--memory ra1shd`。旧版及比较脚本不参与当前构建。
