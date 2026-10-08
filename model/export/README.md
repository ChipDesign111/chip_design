# 参数与向量导出

计划导出权重 INT8、偏置 INT32、量化参数、C 数组和仿真输入。
排序/打包遵守 [MMIO](../../docs/mmio.md)；参数带模型版本和校验值。
固定小型回归样例放 verification/vectors，大规模生成数据放 build。
