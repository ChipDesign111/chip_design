# Component provenance and notices

| 组件 | 位置 | 来源 |
| --- | --- | --- |
| CV32E40P / RI5CY | rtl/platform/cpu_cv32e40p | 保留 ETH Zurich / University of Bologna 等版权和 Solderpad 0.51 声明 |
| AXI / common_cells / Debug | rtl/platform 下的 axi、common_cells、debug | 以具体文件原版权/许可证头为准 |
| 集成、时钟/复位、Boot | rtl/soc 与 rtl/platform 下的 clk_rst、memory | 提供的参考 SoC；不推定所有集成文件使用同一许可证 |
| MLP / 训练产物 | model | 原模型版本、参数、特征/量化/标签与历史指标 |
| UCI HAR 固定输入 | test/2026-10-20/fixtures | Reyes-Ortiz 等（2013），DOI 10.24432/C54S4K；CC BY 4.0、来源行号及SHA保存在provenance.json |
| 可选 SRAM 厂商视图 | tools/local/vendor | 授权本地依赖，不由公开仓库分发 |

75 个保留外围文件在 rtl/manifest.json 记录原相对来源和字节 SHA。路径迁移没有改写版权和源内容。原课程 NPU、专用测试及导入脚本不再保留在当前源码。

此仓库未新增覆盖所有原创文件/训练产物的统一授权声明，见 [LICENSES.md](LICENSES.md)。第三方条款不自动扩展到其他文件。数据来源：[UCI HAR](https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones)。
