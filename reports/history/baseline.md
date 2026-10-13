# Lab 3 外围与 HAR V1 功能基线

2026-10-08；Windows / Python / Icarus 11 / ModelSim 2019.2。
90 个导入文件原字节 SHA 一致。外围与原测试来自用户提供的 Lab 3；两个 NPU 为本次新增实现。

| 测试 | 范围 | 结果 |
| --- | --- | --- |
| check_platform | 外围与原测试/镜像 90 文件 | PASS |
| 原 tb_npu_check | 三组原 4×4 核测试 | ALL PASS，126 个 TB 周期 |
| 原 tb_simple_npu | 三组原 MMIO 用例 | ALL PASS |
| tb_har_core | 1000 组，hidden/score/class 逐值比较 | PASS |
| tb_har_mmio | 12 组及接口边界 | PASS |
| lab3_test1.hex | 真实 CPU、原外围、兼容核 | PASS，7432 SoC 周期 |
| lab3_test2.hex | 同上 | PASS，14754 SoC 周期 |
| lab3_test3.hex | 同上 | PASS，20804 SoC 周期 |
| lab3_hand.hex | 同上 | PASS，208 SoC 周期 |
| HAR 自检 | 真实 CPU、原外围、HAR 六次连续推理 | PASS，64475 SoC 周期 |

SoC 周期从原 TB 释放复位之后统计，含启动、装载、轮询、结果比较和 magic 写回。HAR 每次核心计算 2279 周期，不能与端到端周期混用。

核例覆盖 -128/+127、负得分、零/平局、ReLU、舍入、饱和、极端合法偏置、六类别、复位中止、忙时 START/ACK、DONE 保持。MMIO 覆盖全参数读回、字节排列、无副作用状态读、非法系数/移位保持旧值并报错、忙时写忽略、未定义读返回零。

## 重现

```text
python scripts/check_repo.py
python scripts/run_tests.py --unit
python scripts/run_tests.py --soc --vsim "本机 vsim 路径"
```

原 TB、C 和四镜像不改动。脚本检查真实 SRAM PASS magic，并拒绝 FAIL/TIMEOUT，日志在 build/logs/，结果在 build/results/。

[机器摘要](baseline.json) 包含测试结果、向量与程序 SHA-256。合成种子 20261008，由独立整数参考生成。HAR 程序实际占 6232 字节，指令 2336 字节，测试标志区为 SRAM 0x1FE0–0x1FFF；无函数栈和 C 运行库，后续 C 版本重新预算。

## 限制

当前为功能基线，权重为合成测试数据，未测真实活动识别准确率。存储为寄存器基线，未验证综合资源、目标频率、功耗、FPGA、DRC/LVS/Antenna。外围原有 user 端口未连接警告保留，完整回归无仿真错误；未为消除警告改变外围。
