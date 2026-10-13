# 编译清单

lab3_original.f 为按字节保存的来源清单，不直接运行其中旧路径。scripts/run_tests.py 转换公共外围路径，仅替换 NPU 源为 lab3 或 har 配置，生成 build/lab3.f、build/har.f。单元测试有独立明确的源列表。
不同时编译两份 simple_npu_top，不提交生成的个人绝对路径。原清单包含在 SHA-256 校验中。
