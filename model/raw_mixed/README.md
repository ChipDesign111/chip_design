# 当前 RAW 后端的混合图示例

固定随机权重的 `65→33→5` 演示模型，包含 ReLU、Sigmoid、标量乘法、残差加法与 Softmax。第一个 Linear 使用一块 RAW 和 CPU 边缘，其他小算子使用 CPU。

[make_fixture.py](make_fixture.py) 生成输入、校准及留出输入到被忽略的测试目录。编译、state_dict 导入及完整 SoC 验证见 [编译器说明](../../compiler/README.md)。
