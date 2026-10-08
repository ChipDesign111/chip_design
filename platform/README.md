# 共同平台

[course_soc/](course_soc/README.md) 已选择性导入用户提供的 Lab 3 底座，固定为共有外围基线，90 个文件 SHA 校验。
CPU、AXI、启动、调试、基础存储来自正式模板；保存来源和许可证，必要修复用独立 PR。
现有 my_soc_top/my_npu_subsystem 固定在 course_soc；可变部分为 rtl/npu 的两种配置。没有整包导入个人实验，也没有额外系统顶层。

普通 NPU 开发不改这里。CPU、总线、地址桥和主存保持原字节；运行 python scripts/check_platform.py 校验。不能通过重写 manifest 掩盖外围变化。具体边界和异常修复流程见 [修改与验证指南](../docs/change-guide.md)。
