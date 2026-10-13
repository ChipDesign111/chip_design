# ADR 0001: Fixed platform boundary

Status: Accepted

## Context

CPU、AXI、Debug、启动与主 SRAM 已有稳定集成和原测试。将 NPU 迭代与外围改动混合会扩大回归范围，降低问题定位和来源可追溯性。

## Decision

保持 90 文件快照及其字节校验，NPU 在 rtl/npu 中独立实现。lab3/har 分别编译同名 simple_npu_top，共用固定外部端口、地址转换和下一拍读契约。

## Consequences

内部计算/存储可独立演进。外围修复必须作为独立基线更新，保留原测试与来源，重新执行完整 SoC 回归。固定参考平台不等于已完成目标板卡或工艺适配。
