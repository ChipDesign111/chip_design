# Development guide

## 实现归属

| 区域 | 变更规则 |
| --- | --- |
| `rtl/npu/har/` | 加速器实现、bank 存储、内部调度可修改 |
| `rtl/npu/lab3/` | 兼容配置维护；保留原运算和地址行为 |
| `platform/course_soc/` | 冻结参考外围，不作为普通 NPU 修改区 |
| `verification/lab3/`、`sw/startup/lab3/`、原 filelist | 冻结回归材料 |
| `model/`、自主 verification、scripts、sw | 随规格同步演进 |
| docs / configs / reports | 当前契约、机器规格及版本化证据 |

`rtl/soc/` 为保留目录；`rtl/memory/` 提供可选主 SRAM 适配。当前 MMIO 和权重存储均在 `rtl/npu/har/`，系统顶层在平台目录。架构图见 [architecture.md](architecture.md)。

## 接口契约

simple_npu_top 模块名与端口保持固定：clka、rst_ni、ena、wea、addra[11:0]、dina[31:0]、douta[31:0]。读下一拍有效，写需要 ena && wea，软件完整 32-bit 对齐访问。

地址窗口、状态、错误和数据排列按 [MMIO](mmio.md)，位宽/舍入/饱和/Argmax 按 [整数契约](numerics.md)。内部模块接口可以重构，外部兼容性变化要同步消费者并记录 ADR。

外围缺陷使用独立基线更新：说明来源与修复依据、维护 manifest、保留版权/原测试、完整 SoC 回归。不能单独重写 SHA 消除冻结检查失败。

## 修改步骤

1. 从更新后的 main 创建短期任务分支，明确问题与通过标准。
2. 增加可重现缺陷或新行为的测试，选择最小受影响模块。
3. 新增 RTL 加入真实编译入口，更新规格/固件/参考。
4. 快速调试后运行 [必要验证](verification.md)，记录证据。
5. 提交 PR，审阅后合并；历史报告不替代当前变更检查。

```sh
git fetch origin
git switch -c feat/storage-mapping origin/main
python project.py check
python project.py test --suite unit --count 12
```

## 新增 RTL 的编译入口

当前 `scripts/run_tests.py` 中的 HAR_RTL 被 unit、真实模型和综合后端复用；SoC 的 filelist(profile) 另有对应源列表。新增 har_mac.sv 等文件时，两处均更新，并保持依赖顺序。

两个配置不可同时编译同名 simple_npu_top。不要直接编辑生成的 build/har.f，也不要修改冻结的 lab3_original.f。跨目录模块需要正确路径，不通过伪造目录布局绕过编译。

## 流水和存储修改

单次 39 / 双次 59 周期及 18 重叠断言分布在核级 TB、MMIO TB 和自检生成器；改变流水深度后先推导周期，再同步断言与计数语义。

同步 RAM 的内部延迟需要由调度吸收，保持外围下一拍读契约。验证有效位复位、读回、权重复用、busy 写保护、连续推理和复位中止。RAM 推断成功不等于目标 BRAM/SRAM 宏映射通过。

## 结果与排错

```sh
python project.py test --suite unit
python project.py test --suite model
python project.py test --suite soc --vsim /path/to/vsim
python project.py test --suite model-soc --vsim /path/to/vsim
python project.py synth
```

日志在 build/logs/，程序/模型结果在 build/real_model/，通用综合结果在 build/synthesis/。
核级失败先比 hidden/score；MMIO 失败先查 byte/word 地址和打包；SoC 失败先查镜像装载/CPU 启动，再查请求和返回值。PASS 必须包含实际比较和预期测试数量。

目标发布检查见 [releases.md](releases.md)；缺少目标平台证据时不声明频率、面积、板级或签核完成。
