# 工程工具

project.py：doctor 查看工具，check 检查项目资料，test 运行当前 INT8/训练模型回归，加 --soc 运行商业仿真器上的完整 SoC。
export_tiles.py：将已有模型导出为当前 DMA 的 SRAM tile 字节布局，无 NumPy 依赖。
check_hardware.py：依据 manifest 核对保留外围及已说明的集成覆盖项。
check_repo.py：项目文件、说明链接、Python 语法和 MMIO 元数据检查。
memory_profile.py：授权 SRAM 模型路径/编译方式说明。
download_uci_har.py：下载训练数据。tools/local 是忽略目录，放授权依赖和本机产物。

功能测试详见 [开发与验证](../report/development.md)，EDA 从 [操作指南](../eda/README.md) 开始。
