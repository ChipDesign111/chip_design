# 共有目录与设计架构

状态：DRAFT；2026-10-08。当前目录均为共有项目骨架，尚未导入平台源码或实现 NPU。

## 目录边界

```text
chip_design/
├── platform/course_soc/     共同选定的官方底座
├── rtl/npu/                 自主计算核
├── rtl/memory/              NPU 存储和适配
├── rtl/soc/                 自主包装、顶层与集成
├── model/{reference,training,export}/
├── sw/{include,drivers,tests,startup}/
├── verification/{unit,npu,mmio,soc,vectors}/
├── filelists/
├── scripts/
├── configs/
├── fpga/
├── asic/
├── reports/
└── docs/
```

共有仓库独立于个人 Lab。官方模板通过明确来源和权限检查后导入 `platform/course_soc/`；个人实现按 [贡献规范](../CONTRIBUTING.md) 进入项目目录。

## 硬件层次

```text
CV32E40P / Debug
      ↓
课程 AXI 互连
      ↓
axi2mem
      ↓
har_npu_subsystem（适配与地址转换）
      ↓
har_npu_mmio（寄存器、数据装载、下一拍读出）
      ↓
har_npu_core（层切换、点积、激活量化、Argmax）
      ↔ 权重 / 输入 / 中间结果存储
```

CPU、AXI、启动和调试基础设施优先复用课程模板。团队项目采用自己的顶层和测试；编译清单明确选择模块，避免同时编译同名顶层或两份 CPU。

## 建议新增模块

| 模块 | 职责 |
| --- | --- |
| har_mac | 有符号 INT8 乘法和 INT32 累加 |
| har_dot_engine | 定长点积、偏置及计算完成握手 |
| har_requant_relu | 第一层重新量化、ReLU、饱和 |
| har_argmax | 六个同尺度整数得分取最大值 |
| har_npu_core | 两层调度和状态控制 |
| har_npu_mmio | 控制、状态、数据窗口和结果读回 |
| har_storage | 本地数据存储，隔离仿真 / FPGA / ASIC 实现 |
| har_soc_top | 共同系统集成入口 |

这些是计划中的模块名，不是现有可运行 RTL。

## 计算架构

V1：一个 MAC，顺序处理每个神经元，复用计算单元完成两层。先形成正确的完整网络。
V2：在实际综合与性能数据支持下评估四路乘法，明确存储带宽和流水线后再实施。

理想乘加周期分别约 2,240 和 560；两者都未包含装载、存储访问、偏置、量化、控制及读回，不作为承诺延迟。

## 构建边界

- 共有脚本从任意当前目录调用时，自行定位仓库根目录。
- 原模板 filelist 的相对路径不能直接当作共有路径使用。导入时记录原工作目录，项目 filelist 以约定根目录解析。
- 后续可由脚本展开绝对编译路径，生成到 `build/filelists/`，不把个人绝对路径提交。
- 原 Lab 测试配置与 HAR 配置有独立 filelist 和 testbench。HAR 不以旧 4×4 测试作为功能验收。
- 仿真程序镜像由配置指定，避免为了切换测试频繁改 RTL。
- SRAM 初始化机制仅代表仿真或 FPGA 支持；ASIC 存储初始化另按课程要求实现。
