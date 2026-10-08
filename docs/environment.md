# 环境和共有运行入口

已验证：Windows、Python 3.11、Icarus Verilog 11、ModelSim 2019.2。工具路径使用 PATH 或 CLI 参数，不写个人绝对路径。

```text
python scripts/check_repo.py
python scripts/check_platform.py
python scripts/run_tests.py --unit
python scripts/run_tests.py --soc --vsim "本机 vsim 路径"
```

从根目录执行；脚本也支持从其他目录调用。不带 --unit/--soc 时执行全部。Icarus 不在 PATH 时指定 --iverilog、--vvp。--count 支持 12–1000，默认核级 1000 组。

完整 AXI SoC 使用 ModelSim，Icarus 11 不支持这里的 SystemVerilog interface。独立 work 在 build/soc/lab3/、har/；多人各自克隆，同一克隆勿同时跑两份回归。

## ModelSim

使用已有 LM_LICENSE_FILE；未配置时仅尝试 vsim 安装目录上一级的 LICENSE.TXT。其他安装布局请自行配置环境变量。许可证不提交。

原 SoC TB 不改动。运行脚本用 -G 指定 SRAM INIT_FILE，启动后关闭 VCD 以减少回归开销。检查真实 SRAM magic=c0dec0de 才判通过；FAIL、TIMEOUT、缺失 PASS、编译错误均失败，不能把 $finish 的零退出码当 PASS。

## 向量与程序

```text
python scripts/generate_vectors.py --count 1000
python scripts/build_har_firmware.py
```

种子 20261008，向量通过独立 Python 整数参考生成。
HAR RV32I 编码器不依赖交叉编译器，生成实际 CV32E40P 执行的 8 KB hex、解释性 .S 清单和地址/SHA JSON。清单不是完整 GCC 工程；后续 C 驱动需建立交叉编译链。

原 Lab 3 四份预编译 hex 直接使用，原 C/启动/链接材料保留。
日志在 build/logs/，结果在 build/results/unit.json、soc.json；见 [报告](../reports/baseline.md)。
GitHub CI 执行外围校验和 Icarus 单元回归，商业 SoC 仿真本地执行。

FPGA/ASIC 尚未验证，板卡、频率和工艺约束待确认。PDK、标准单元库及许可证留在课程指定环境，不提供给 AI、不上传。
