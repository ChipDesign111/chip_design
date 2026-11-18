# FPGA构建与装载

器件为A7-35T xc7a35tcsg324-1，系统时钟20MHz。当前main未重新完成FPGA实现或上板，见[当前状态](TEST_REPORT.md)；旧板测证据仅在[历史入口](../report/history.md)查阅。

| 文件 | 用途 |
| --- | --- |
| final_project/ | Vivado工程及当前RTL源清单 |
| fpga_top.sv / fpga_top.xdc | 板级包装和时钟/引脚约束 |
| configure_final_project.tcl | 配置工程、顶层和约束 |
| build_final_project.tcl | 构建预装载专用自检镜像 |
| build_direct.tcl | 独立构建入口，参数以脚本为准 |
| connect_fpga.tcl | 动态发现当前JTAG目标，避免复用旧序列号 |
| prepare_jtag_image.ps1 | 将2048个HEX字转换为8KiB小端BIN |
| load_soc_image.gdb | 通过Debug写镜像及启动提交 |
| firmware/ | 保留的兼容专用自检固件；不代表新通用网络已板测 |

```powershell
vivado -mode batch -source fpga/configure_final_project.tcl
vivado -mode batch -source fpga/build_final_project.tcl
powershell -File fpga/prepare_jtag_image.ps1 -InputHex path/to/firmware.hex
```

预装载模式显式提供SRAM_INIT_FILE；无预装载时为空，不填写包含两个引号字符的字面值。fpga_top默认空参数。当前build_final_project.tcl显式使用firmware/int8_selftest.hex，运行新编译镜像须选择正确初始化文件，或构建无预装载版后经JTAG加载。

ASIC默认SRAM无初始化。JTAG重装前停机/复位，顺序写满2048个完整字、读回核对，再写Boot提交密钥。不能将旧bitstream、旧板级周期或ASIC的2700拍直接当作本版板测结果。
