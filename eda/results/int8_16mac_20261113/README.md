# INT8 main：16-MAC 完整 EDA 结果

本轮从 `main` 的 RTL 提交 `29f6b88` 重新综合并完成 Innovus 01–34 步，结果文档提交为 `c02527e`。含 PAD 的整颗 Die 为 **3.7956390976 mm² ≤3.8 mm²**，最终有效逻辑密度 **72.509% ≤75%**。20 ns 时钟下最终 Setup/Hold 为 **+0.335/+0.050 ns**。

## 结果

| 指标 | 上一版高密度诊断 | 本轮 16-MAC |
| --- | ---: | ---: |
| 综合 Cell Area | 2.154019 mm² | **2.023901 mm²** |
| 映射实例 | 69,317 | **66,348** |
| NPU subsystem | 0.905127 mm² | **0.775048 mm²** |
| NPU core | 0.570298 mm² | **0.472980 mm²** |
| Placement density | 77.007% | **71.61%** |
| 最终有效密度 | 79.37% | **72.509%** |
| Setup WNS | +0.111 ns | **+0.335 ns** |
| Hold WNS | +0.050 ns | **+0.050 ns** |

与上一版相比，综合 Cell Area 减少 **130,118.285 µm²，6.04%**；NPU subsystem 减少 **130,078.771 µm²**。PAD 外围和 `3.8 mm²` Die 尺寸没有改变，密度下降来自 RTL 计算阵列和 bias 存储收缩。

## 功能与周期

用户本地完整 `run.py --count 32 --trained --soc` 回归通过。batch=4 完整 SoC：

```text
testbench cycles = 2700
hardware cycles  = 2695
NPU cycles       = 952
FC1 issue        = 512
FC2 issue        = 64
DMA read overlap = 466
DMA write overlap= 499
```

FC1 改为 4 个 `8 输出×2 lane` phase，16-MAC 每 tile 计算 16 拍，与 16 拍权重读取重叠；FC2 保持 4 个 `6 输出×2 行` phase，只使用 12 个乘法器。bias1/bias2 内部存储均收为 INT22。

## 时序与物理检查

最差 Setup 路径从 `i_sram_transaction_reset/reset_qualified_n_reg/Q` 到 `i_npu_subsystem/i_npu_core/douta_reg[28]/D`，Slack `+0.335 ns`。最差 Hold 路径从 `i_bootram/soc_cycles_reg[24]/Q` 到 `i_bootram/data_o_reg[24]/D`，Slack `+0.050 ns`。

最终检查结果：

- Setup/Hold TNS=0，违规路径=0。
- max-cap、max-tran、max-fanout、max-length 的 Real/Total 均为 0。
- 未放置实例=0，default DRC=0，天线违规网络=0。
- 完整核心 VDD/VSS PG 检查无问题或警告。
- 常规信号连接未解决问题=0；`VDDPST/VSSPST` 两项 IO 库抽象限制由同源步骤 22 原生电源轨证据分类。
- DEF、SDF、SPEF、GDS、层次/平坦网表已导出并完成结构对应检查。

## 身份与保留位置

```text
部署提交:       c02527ec96cd4cf5d31c0a903c9e57e03f5ad107
RTL 功能提交:   29f6b88
上传包 SHA256:  dd497943898e3bc44f2eac7d40b5907bf072dd89abe0771e2d66f47faf60c3b9
输入清单 SHA256: 84bcbc854981aa8b2c0029861251fa3ab0018d34d3c585e5c73b1c53ed2b9805
```

34 个 `step_*.json` 均引用同一输入清单。轻量回传包为 `review_delivery.tar.gz`，SHA-256 为 `263428b9a5ba9c2f61a46ace4fd27f08ee9fa77c24d3f89271eb999c0c2a7561`。GDS、DEF、SPEF、SDF、平坦网表和 EDA 数据库保留在服务器上传目录，路径与 SHA 见 [summary.json](summary.json)。

本结果范围是 TT/1.8 V/25°C、SI 关闭的单工艺角工具流程。未执行 SDF 回标后仿、独立 foundry DRC/LVS、多 PVT、IR/EM/ESD 或形式等价。
