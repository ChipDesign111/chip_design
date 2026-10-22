# Main SRAM

## 实现与资料

rtl/memory/my_mainmem.sv 和 chip_sram_2048x32.sv 实现 2048×32、8192 B 单端口主存。默认 portable-sram 使用项目自有行为存储；--memory ra1shd 连接授权本地模型。旧 reference 实现已移除，SoC 只编译一份 my_mainmem。

九个原始 SRAM 文件保留在 tools/local/vendor/RA1SHD_2048x32M8，清单为 tools/local/vendor/local-inventory.json。目录迁移前后逐文件 SHA 一致。tools/local 整体忽略，不上传原始 Verilog、Liberty、CDL 或版图资料。fpga 保持空占位；[EDA](../eda/README.md) 使用服务器授权库执行工艺映射和前后仿流程。

## 接口

CPU 地址基址 0x80000000，word 地址 addr[12:2]；CLK=clk_i，CEN=~req_i，WEN=~(be_i & {4{we_i}})，D/Q 为 32 bit，OEN=0。读在上升沿采样后返回，读不受 be 值影响；req 无效不写。写期间 Q 不作为有效读值，不规定旧值/新值语义。

宏无数据复位，上电内容未定义。旧 SoC 功能测试台在 CPU 复位期间通过实际端口写入镜像，并适配启动字；不访问厂商内部数组，不注入 PASS。外部引脚验证使用顶层 JTAG 下载并回读全部程序字，再发布启动字和复位运行，见 [启动协议](../eda/BOOT_PROTOCOL.md)；各阶段的实际验收状态见 [EDA 结果](../eda/RESULTS.md)。

## 验证

```sh
python tools/project.py test --suite memory
python tools/project.py test --suite memory --memory ra1shd
python tools/project.py test --suite soc --memory ra1shd --vsim /path/to/vsim
python tools/project.py test --suite model-soc --memory ra1shd --vsim /path/to/vsim
python tools/project.py synth
```

SRAM 单元覆盖 2048 地址、16 字节掩码、禁写、随机读写、同步采样和复位保持。完整 SoC 使用当前 MLP 自检，原 4×4 程序不再运行。

厂商模型在零延迟 RTL 中使用明确的 +notimingchecks 功能模式；Icarus 不启用 specify。它不证明 setup/hold、目标频率或 STA/SDF 通过。Yosys 仅检查 65536-bit 同步 RAM 与单 blackbox 连接，不读取厂商 Liberty/CDL/版图内容。

此宏用于 CPU 主存，不能直接折叠 NPU 的 38 个并行权重 bank。目标工艺映射、面积、时序和后端验收单独记录于 [EDA 结果](../eda/RESULTS.md)。历史 SRAM 测试见 [2026-10-15](../test/2026-10-15/sram-integration/report.md)，该记录保留旧目录和配置语境。
