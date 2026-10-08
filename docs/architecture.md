# 共有架构：外围固定，NPU 可变

状态：LAB3_PERIMETER_FIXED / HAR_V1_IMPLEMENTED；2026-10-08。

外围使用用户提供的 Lab 3 底座。CPU、AXI、Debug、Boot RAM、8 KB 主 SRAM、复位、my_soc_top、my_npu_subsystem 保持导入内容，原字节 SHA-256 校验。变动点仅在 NPU。

```text
my_soc_top                         platform/course_soc/soc/rtl/
├── CV32E40P                      platform/course_soc/cpu_cv32e40p/
├── AXI / Debug / Boot RAM / SRAM
└── my_npu_subsystem              固定 axi2mem 与地址转换
    └── simple_npu_top            按编译配置选择
        ├── lab3: simple_npu_core + 4×4 PE
        └── har: har_npu_core + 本地参数/输入/结果寄存器
```

NPU 端口沿用 Lab 3：clka、rst_ni、ena、wea、addra[11:0]、dina[31:0]、douta[31:0]。地址转换为 addr[13:2]，读下一拍有效，写需要 ena && wea。软件仅用完整 32 位对齐访问。基址 0x70000000，高地址别名沿用固定外围。

## 两个编译配置

| 配置 | 可变代码 | 用途 |
| --- | --- | --- |
| lab3 | rtl/npu/lab3/ | 无符号 4 位、4×4 原课程回归 |
| har | rtl/npu/har/ | 有符号 INT8、64→32→6 完整 MLP |

两个配置同名 simple_npu_top，每次只编译一份。没有新增 har_soc_top 或第二份 CPU。scripts/run_tests.py 从 [原 filelist](../filelists/lab3_original.f) 展开共有路径并替换 NPU 项，生成 build/lab3.f、build/har.f。

## 文件安排

| 位置 | 内容 |
| --- | --- |
| platform/course_soc/ | 选定外围及 manifest.json 原字节校验 |
| rtl/npu/lab3/ | 本次编写的兼容核 |
| rtl/npu/har/ | 本次完整 HAR V1 |
| verification/lab3/ | 原核级、MMIO、SoC 测试及 C/hex，字节不变 |
| verification/npu/、mmio/ | 新 HAR 测试 |
| model/reference/mlp_int.py | 独立 Python 整数参考 |
| scripts/build_har_firmware.py | 由真实 CPU 执行的 RV32I 自检生成器 |
| sw/startup/lab3/ | 原启动/链接材料，不用于生成器路径 |
| build/ | 向量、程序、work、波形、日志、结果；忽略 |
| reports/ | 验证摘要 |

来源是用户提供的 lab3-ST/SoC_cv32e40p，未整包复制个人实验；不声称等同未经修改的上游发行包。原文件禁止 Git 行尾转换，清洁克隆可校验原 SHA。见 [来源](../platform/course_soc/README.md)。

## V1 实现

一个有符号 MAC 顺序计算两层；2279 周期 = 2240 MAC + 32 hidden 保存 + 6 score 保存 + 1 Argmax，不含 CPU 传输。参数及输入采用可综合寄存器和动态索引，复位清零。

当前为功能基线，尚无面积、最高频率或功耗证据。后续 SRAM/FPGA 存储适配和并行优化在 NPU 内进行，保持外围接口。数值和地址契约变更必须同步软件、参考和回归。
