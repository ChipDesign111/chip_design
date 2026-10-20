# INT8 兼容实现

`simple_npu_top.sv` 提供原MMIO接口，`har_npu_core.sv` 提供单/双样本INT8流水核心。未定义 `CHIP_STREAM_NPU` 时实例化本目录。共享tile和权重bank位于 [../common](../common/)，目录名称不改变模块名。

本实现用于兼容回归；版本性能基准的前一版RTL由脚本从提交52be8c5独立取出，不能用当前baseline或最终版诊断模式替代真实旧版本。

验证：`python tools/project.py test --suite unit`、`--suite model`、`--suite model-soc --vsim /path/to/vsim`。最终W8A4开发入口见 [上级说明](../README.md)。
