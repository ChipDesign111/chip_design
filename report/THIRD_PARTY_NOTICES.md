# Component provenance and notices

| 组件 | 位置 | 来源 |
| --- | --- | --- |
| CV32E40P / RI5CY | rtl/cpu_cv32e40p | 保留 ETH Zurich / University of Bologna 等版权和 Solderpad 0.51 声明 |
| AXI / common_cells / Debug | rtl/axi、common_cells、debug | 以具体文件原版权/许可证头为准 |
| 集成、时钟/复位、Boot | rtl/soc、clk_rst、memory | 提供的参考 SoC；不推定所有集成文件使用同一许可证 |
| MLP / 训练产物 | model | 原模型版本、参数、特征/量化/标签与历史指标 |
| UCI HAR 固定输入 | test/2026-10-15/fixtures | Reyes-Ortiz 等（2013），DOI 10.24432/C54S4K；CC BY 4.0、来源行号及 SHA 保存在 fixture |
| 可选 SRAM 厂商视图 | tools/local/vendor | 授权本地依赖，不由公开仓库分发 |

75 个保留外围文件在 rtl/manifest.json 记录来源和字节 SHA。2026-10-20 至 21 日修改 bootram 默认首条指令，并在 SoC 顶层增加下降沿复位释放寄存器；原 SHA、新 SHA 和原因通过 `project_override`、`integration_history` 保留，见 [启动与复位协议](../eda/BOOT_PROTOCOL.md)。清单保留此前两处 DMA 集成修改的原哈希；共有三个集成文件有修改，其余 72 个保持原始课程字节，既有版权不变。原课程 NPU、专用测试及导入脚本不再保留在当前源码。

此仓库未新增覆盖所有原创文件/训练产物的统一授权声明，见 [LICENSES.md](LICENSES.md)。第三方条款不自动扩展到其他文件。数据来源：[UCI HAR](https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones)。
