# 从 main 保留的 Vivado 工程

本分支主要验证服务器 TSMC180 ASIC 流程。保留 main 更新的 Vivado 2019.1 工程、A7-35T 引脚和时钟生成配置；当前 filelist 及 firmware/int8_selftest.hex 已适配 batch=4、共享 32 乘法器、FC2 打包和 W2 预取，FPGA 系统时钟为 25 MHz。

使用 configure_final_project.tcl 重新生成源清单；该脚本写入当前机器的固件绝对路径，并使用 `Flow_AreaOptimized_high` 综合、默认 implementation。旧并行架构在 main 的 LUT 超限结论属于旧实现；本分支没有重新宣称板上运行或 Vivado 面积已验证。固件从 test/int8/firmware.py 生成，CPU 通过 MMIO 做训练模型四个样本自检。

`vivado_init.tcl` 会加载 `connect_fpga.tcl`，注册 `har_connect_fpga` 和
`har_program_fpga` 两个 Tcl 命令。前者动态选择真正包含 `xc7a35t` 的在线目标，
避免复用上次会话缓存的序列号；后者接受 bitstream 路径并完成烧录。

初始化脚本还会预加载并包装 Hardware Manager 的 `open_hw_target`。GUI 的
`Auto Connect` 发起无参数 `open_hw_target` 时，动态发现将自动选择当前的
A7-35T；缓存目标 `21051218003` 也会被替换。显式打开其他有效目标时仍原样
透传。启动后可用下面的命令确认钩子已启用：

```tcl
info body open_hw_target
```

## 通过 JTAG 更换固件镜像

T07 及后续多镜像板级测试使用 `SRAM_INIT_FILE=""` 的无预装载 bitstream。
该 bitstream 上电后 CPU 不取指，调试模块通过 JTAG 保持可访问。每次复位后，
按地址顺序向 `0x80000000` 写入完整的 2048 个 32 位字，再向
`0x0001003C` 写入 `0xB007C0DE` 释放 CPU。

先将 2048 个十六进制字转换成小端二进制：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File fpga/prepare_jtag_image.ps1 `
    -InputHex fpga/firmware/int8_selftest.hex `
    -OutputBin fpga/firmware/int8_selftest.bin
```

在 GDB 中加载项目提供的命令：

```gdb
source D:/LiChade/PKU/major/AdvanceChip/chip_design/chip_design/fpga/load_soc_image.gdb
soc-boot-status
soc-load-bin D:/LiChade/PKU/major/AdvanceChip/chip_design/chip_design/fpga/firmware/int8_selftest.bin
soc-boot-status
soc-commit-image
```

`prepare_jtag_image.ps1` 要求输入恰好 2048 个十六进制 32 位字，并检查输出
文件为 8 KiB。`soc-load-bin` 按地址顺序装入镜像，并检查 Boot 控制器计数达到
2048、`boot_ready` 仍为零。`soc-commit-image`
只在上述条件满足时写启动密钥，并等待 `boot_ready=1`。

更换镜像前必须复位 SoC，使 `loaded_words` 回到零。该流程仅适用于无预装载
bitstream；预装载 bitstream 的 `PREINITIALIZED=1`，CPU 不等待 JTAG 装载。
