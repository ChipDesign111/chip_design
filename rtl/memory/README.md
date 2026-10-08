# NPU 存储适配

计划隔离权重、偏置、输入和中间结果的接口，以及仿真、FPGA、ASIC 的底层实现。
先明确带宽、延迟、装载和复位；以试综合检查触发器或存储宏实现。
详见 [存储预算](../../docs/memory-budget.md)。
当前只有预留说明，实际 NPU 本地存储在 rtl/npu/har/simple_npu_top.sv。拆出模块时同时加入 scripts/run_tests.py 的 HAR 单元与 SoC 源列表，保持外围读延迟、装载和复位行为；见 [修改与验证指南](../../docs/change-guide.md)。
