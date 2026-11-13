# 开发与验证

本次集成基于 rtl-dev `1eb6462`，移入 perf/ifetch-line-buffer `5da2148` 的取指缓存并修复非缓存地址、写入一致性和异常填充处理，同时修复单样本 Argmax 的旧值比较。当前 NPU 保持 batch=4、零气泡 tile 交接、FC2 八 tile 打包和 W2 跨层预取，并将共享 INT8 乘法器从 32 个收为 16 个：FC1 改为四个 8 输出×2 lane 相位，FC2 仍为四个 2 行×6 输出相位并只使用 12 个乘法器；内部累加器和 bias 存储均为 INT22。用户本地完整回归通过，batch=4 SoC testbench/硬件为 2700/2695 拍、NPU 为 952 拍、FC1/FC2 发射为 512/64，DMA 读/写重叠为 466/499。同源 34 步 EDA 也已完成：最终密度 72.509%，Setup/Hold 为 +0.335/+0.050 ns。最终数据库的 10 组 MAXIMUM SDF 和 1 组 unit-delay 对照功能通过 11/11，工作窗口动态时序违规为 0。当前 ASIC RTL 保留 `CUT_SLV_AX` 地址通道边界；FPGA bitstream 也必须从当前源码重新构建验证。

```bash
python tools/project.py doctor
python tools/project.py check
python test/int8/run.py --count 32 --trained --soc
python test/int8/perf.py
python tools/export_tiles.py --output tools/local/int8_tiles
```

run.py 创建独立 test/int8/runs/时间戳，记录单元和 SoC 日志。32 组随机批次覆盖单样本、双样本和四样本，以及 INT8 极值、舍入/饱和、累加回绕；6 组训练模型四样本批次覆盖固定的 24 条 UCI 输入。真实 SoC 使用 Debug SBA 请求边界注入装载事务，事务穿过实际 AXI 适配器和交叉开关；不以直接改 SRAM 数组或注入完成标志代替 CPU 执行。

单元回归还检查 tile 不提前释放、不覆盖有效 bank、进入 FC2 前已经发起 W2 预取、读失败不发布、复位中断与重新启动。随机数据同时覆盖 INT22 正负极值 bias 和补码回绕；训练模型的 24 条输入要求与历史 INT32 逐值一致。完整 SoC 检查无镜像/部分镜像/乱序/字节写/错误时机密钥不会放行，CPU 启动后通过 MMIO 驱动 NPU 并逐值自检。固定权重下的逐步周期对比如 [performance.md](performance.md)。

ModelSim 测试是 RTL 行为仿真。工艺综合、布局布线和导出依照 [EDA 指南](../eda/README.md) 在服务器完成。CI 只运行开源功能子集，不伪称执行了商业工具或 SDF 后仿。原生宏模型、PDK 和开发临时工具留在本地/服务器授权目录。
