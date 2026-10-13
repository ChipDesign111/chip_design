# Verification strategy

## 判定目标

硬件正确性要求与整数参考逐值一致：32 个 hidden、6 个 score、class、状态与计数。模型准确率单独与真实标签比较。分类错误不能被误报为硬件算术错误，也不能通过调整参考答案掩盖 RTL 错误。

冻结的原平台测试保持原样，独立 HAR 测试负责新工作负载。合成极值、真实数据和真实 CPU 各自覆盖不同风险。

| 层级 | 覆盖 | 命令 |
| --- | --- | --- |
| 仓库 / 平台 | 文档链接、Python 语法、配置、90 文件 SHA | `project.py check` |
| 算术 / 控制 | 1000 参数组，单/双模式、复位、START/ACK、状态保持 | `project.py test --suite unit` |
| MMIO | 打包、下一拍读、非法配置、忙时写保护、同步读回 | 同 unit |
| 已选模型 | 独立 NumPy/标量参考、真实输入逐值对照 | `project.py test --suite model` |
| 完整平台 | 原四镜像、加速器八次/六次程序 | `project.py test --suite soc` |
| 真实模型 SoC | 真实 CV32E40P、固定 AXI、24 条六类输入 | `project.py test --suite model-soc` |
| 通用结构 | RAM、同步端口、乘法器和锁存器 | `project.py synth` |

实际调用形式为 `python project.py ...`。全数据集参数见 [环境文档](environment.md)。

## 通过条件

必需测试完整运行并返回成功；缺失 PASS、FAIL、TIMEOUT、编译错误均失败。SoC 需要真实 CPU 写入 SRAM 的 `c0dec0de`；原 TB 不通过强制写标志或替换期望获得 PASS。

单 / 双模式周期断言为 39 / 59；双模式重叠 18 周期，两级每样本活跃 19 周期。改变架构后须先推导新边界，再联动自主断言、固件和规格。不得仅删除断言。

## CI 与本地证据

公共 CI 独立执行 Repository policy、RTL regression、Trained model、Generic synthesis 四项，保留日志和结构化结果。模型 CI 使用六类 24 条固定真实输入，无需网络下载原始数据。

完整商业 SoC、全 2947 条测试和目标平台流程在对应环境运行。CI 绿色不代表这些未执行的检查已完成。

报告记录被验证 revision 或源 SHA、工具、命令、模型/向量 SHA、数量、结果和限制。已记录的历史基线不随脚本改动自动变成新版本证据；见 [报告索引](../reports/README.md)。

## 变更对应的验证

文档变更执行仓库/平台检查。入口、源清单或 CI 变化还需要实际调用受影响工作流并在干净 checkout 复现。RTL、MMIO、数值、存储与固件变化执行相关完整 unit/model/SoC 回归，目标实现变化增加目标平台检查。

失败样例保存为固定回归。首次定位按“整数参考 → hidden → score → MMIO → CPU/总线”的层次收敛，避免同时猜测修改多个层级。
