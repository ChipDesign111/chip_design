# Main SRAM integration

## 资料与实现位置

本地原始资料位于 `asic/vendor/RA1SHD_2048x32M8/`。九个文件移动前后逐文件 SHA-256 一致，原目录已移走，本地清单为 `asic/vendor/local-inventory.json`。文件带有机密/专有声明，不进入公开 Git 历史、CI 或发行包；取得授权的成员在各自环境配置原始资料。

| 文件 | 职责 |
| --- | --- |
| [chip_sram_2048x32.sv](../rtl/memory/chip_sram_2048x32.sv) | 单端口接口、低有效引脚转换、自有行为后端 |
| [my_mainmem_sram.sv](../rtl/memory/my_mainmem_sram.sv) | 保持主存端口和字节地址转换的替代实现 |
| [ra1shd_blackbox.sv](../asic/ra1shd_blackbox.sv) | 自主编写的接口声明，仅用于连接检查 |
| [tb_mainmem_sram.sv](../verification/unit/tb_mainmem_sram.sv) | 全地址、掩码、禁写、随机及复位保持测试 |
| [tb_soc_sram.sv](../verification/soc/tb_soc_sram.sv) | 仿真装载和 CPU 完成标志被动监测 |
| [memory_profile.py](../scripts/memory_profile.py) | 编译源、模型依赖、测试顶层选择 |

冻结平台、原测试和原 filelist 不改写。构建脚本展开原清单时替换主存实现和测试顶层，每次只编译一个 my_mainmem。

## 接口与复位

容量 2048×32 bit = 8192 B，单时钟、单端口，4 个字节写使能。CPU 基址仍为 `0x80000000`，word 地址取 `addr[12:2]`，高位别名行为与原平台一致。

| 项目信号 | 宏连接 |
| --- | --- |
| clk_i | CLK |
| req_i | CEN = ~req_i |
| byte_we_i = be_i & {4{we_i}} | WEN = ~byte_we_i |
| addr_i[12:2] | A[10:0] |
| wdata_i / rdata_o | D[31:0] / Q[31:0] |
| 输出使能 | OEN = 0 |

有效读在上升沿采样后返回，沿用一拍读契约。读不受 be 的值影响；req 无效不得写入。写期间 Q 不作为有效读数据使用，不规定 read-during-write 返回旧值或新值。

宏无数据复位，上电内容未定义，复位不擦除主存。INIT_FILE 不是硬件宏功能。新 TB 在 CPU 复位期间通过实际存储端口装入镜像，再释放端口并启动 CPU；不访问厂商内部数组、不注入 PASS 标志。硬件部署仍需独立程序装载方案，仿真装载不等于 Boot ROM 已具备下载能力。

## 编译与验证

| --memory | 主存实现 | 依赖 / 范围 |
| --- | --- | --- |
| reference（默认） | 原 my_mainmem + sram_ff | 原始回归、保持旧命令行为 |
| portable-sram | 新适配器 + 自有行为存储 | 公开功能测试，不含厂商模型 |
| ra1shd | 新适配器 + 本地厂商 Verilog | 授权环境的模型功能验证，缺失模型即失败 |

memory 套件默认 portable-sram；soc / model-soc 默认 reference。--memory 不作用于 NPU unit / model，入口拒绝这些显式组合。

```sh
python project.py test --suite memory
python project.py test --suite memory --memory ra1shd
python project.py test --suite soc --memory ra1shd --vsim /path/to/vsim
python project.py test --suite model-soc --memory ra1shd --vsim /path/to/vsim
python project.py synth
```

portable-sram 同样支持 soc / model-soc；完整 SoC 需要 ModelSim。公开 CI 只执行自有存储功能测试与通用结构检查。结果在 build/results，清单、数据库和日志在忽略的 build；含厂商资料的本地产物不得作为公开源码或 CI 产物提交。

厂商模型含 setup/hold 检查。零延迟 RTL 在同一仿真时刻改变时钟与输入，不能验证物理保持时间。ra1shd 的 SoC 命令明确使用 ModelSim `+notimingchecks` 做功能验证；Icarus 单元测试也未启用 specify 时序检查。没有添加 RTL 延迟模拟物理路径，未宣称时序通过。目标 STA / SDF 须在真实约束和映射环境单独完成。

## NPU 与后端边界

此单端口宏用于 CPU 主 SRAM。NPU 的 38 个权重 bank 支持两层并行读取及独立 CPU 回读；直接折叠为单宏会造成端口/带宽冲突。NPU 的 39 / 59 周期和 18 周期重叠不变。权重宏映射需要独立评估 bank 利用率、端口复制/仲裁及流水调度。

本地资料包含 Verilog、五个角的 Liberty、CDL、antenna LEF 和 vclef。当前流程只运行 Verilog，不读取 Liberty/CDL/版图内容。授权 EDA 环境仍需选择角、确认物理视图及电源连接，完成 STA、DRC/LVS、天线等检查。目录未提供独立 GDS 文件，不能据此声称已有完整流片视图。

Yosys 通用检查仅验证自有后端推断 1 个 65536-bit 同步 RAM，以及宏后端保留 1 个 blackbox 且无锁存器。接口声明没有厂商时序或几何，不能代替工艺库绑定与签核。
