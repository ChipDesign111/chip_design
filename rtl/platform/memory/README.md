# Boot 与 8 KiB 主 SRAM

| 文件 | 作用 | 维护方式 |
| --- | --- | --- |
| bootram.sv / bootrom.sv | 课程提供的 Boot 存储 | 保留原字节，由manifest校验 |
| my_mainmem.sv | SoC 主存访问接口 | 项目维护，保持既有端口与读写时序 |
| chip_sram_2048x32.sv | 2048×32存储与后端选择 | 默认portable-sram，本地可选ra1shd |
| ra1shd_blackbox.sv | SRAM 端口连接声明 | 自主声明，不含厂商实现 |

主存复位不擦除，上电内容未定义。仿真中测试台在CPU复位期间通过SRAM端口装载镜像。NPU的2240 B权重bank在 `rtl/npu/common/`，与这块单端口主SRAM独立。

从仓库根目录运行 `python tools/project.py test --suite memory`；有授权模型时加 `--memory ra1shd`。改动主存后还需运行两种配置的完整SoC与 `python tools/project.py synth`。后端接入、授权路径和时序边界见 [SRAM说明](../../../report/sram.md)。
