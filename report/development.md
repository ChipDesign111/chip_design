# 开发与验证

基于 main 267c873 的 xzx 是唯一当前实现；旧 xzx 分支、旧 RTL/测试和旧 EDA 证据已保存在本地 archives，Git bundle 已验证可恢复。

```bash
python tools/project.py doctor
python tools/project.py check
python test/int8/run.py --count 32 --trained --soc
python tools/export_tiles.py --output tools/local/int8_tiles
```

run.py 创建独立 test/int8/runs/时间戳，记录单元和 SoC 日志。32 组随机批次覆盖单/双样本、INT8 极值、舍入/饱和、累加回绕；12 组训练模型批次覆盖固定的 24 条 UCI 输入。真实 SoC 使用 Debug SBA 请求边界注入装载事务，事务穿过实际 AXI 适配器和交叉开关；不以直接改 SRAM 数组或注入完成标志代替 CPU 执行。

单元回归还检查 tile 不提前释放、不覆盖有效 bank、读失败不发布、复位中断与重新启动。完整 SoC 检查无镜像/部分镜像/乱序/字节写/错误时机密钥不会放行，CPU 启动后通过 MMIO 驱动 NPU 并逐值自检。

ModelSim 测试是 RTL 行为仿真。工艺综合、布局布线和导出依照 [EDA 指南](../eda/README.md) 在服务器完成。CI 只运行开源功能子集，不伪称执行了商业工具或 SDF 后仿。原生宏模型、PDK 和开发临时工具留在本地/服务器授权目录。
