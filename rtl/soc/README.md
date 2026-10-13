# SoC 集成

当前为预留目录，未参与构建。系统顶层 my_soc_top 和桥接 my_npu_subsystem 位于 platform/course_soc 并已冻结；MMIO 包装在 rtl/npu/har/simple_npu_top.sv，不在这里重复建系统顶层。
未来若有独立集成需求，先明确冻结边界和编译配置。见 [修改与验证指南](../../docs/change-guide.md) 及 [MMIO 契约](../../docs/mmio.md)。
