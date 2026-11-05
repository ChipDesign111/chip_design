# RTL 周期优化：交叉开关直通（FallThrough）实验（2026-11-04）

目标：不改测试台，只改 RTL，让同样一份固件在芯片上跑更少的周期。结论：把 `axi_xbar` 的 `FallThrough` 由 `1'b0` 改为 `1'b1`，单词 SBA 写从 **4 拍/字降到 3 拍/字**，装载窗口 **−2,054 拍**，端到端（到 CPU 自检 PASS）**−2,063 拍（−17.3%）**，功能与重叠计数不变。

## 1. 根因

RTL 探针（`tb_probe.sv`，逐拍打印 DM 适配器、xbar 从端口与 `axi2mem` 状态）显示，一笔单词写的三拍是：

| 拍 | 现象 | 说明 |
| --- | --- | --- |
| A | `aw_valid=1, aw_ready=1, w_valid=1, w_ready=0` | AW 被接受，W 没有被接受 |
| A+1 | `w_ready=1, gnt=1`，`sram_req=1` | W 才被接受，同时发出存储请求 |
| A+2 | `b_valid=1` | 写响应回到 DM 适配器，下一笔才能重新进入 IDLE |

AX（地址）与 W（数据）在同一拍发出，却在不同拍被接受。原因在 xbar 的 W 通道：`axi_mux` 用 `fifo_v3(FALL_THROUGH=FallThrough)` 保存“本拍仲裁给了哪个从端口”，`FallThrough=0` 时该 FIFO 寄存一拍，W 只能按上一拍的仲裁结果路由，于是比 AW 晚一拍。适配器因此进入 `WAIT_LAST_W_READY`，白等一拍。

探针实测（`tb_probe.sv` 输出，单位 10 ns）：

```
P4  ad=3 oc=0 req=1 gnt=1 | slv2 awv=0 awr=0 wv=1 wr=1 bv=0 | sram req=1 we=1 a=80000080 | a2m=4
P5  ad=1 oc=0 req=1 gnt=0 | slv2 awv=0 awr=0 wv=0 wr=0 bv=1 | sram req=0 we=0 a=00000000 | a2m=3
P6  ad=0 oc=0 req=1 gnt=0 | slv2 awv=1 awr=1 wv=1 wr=0 bv=0 | sram req=0 we=0 a=80000084 | a2m=0
```

（`ad`：IDLE=0 / WAIT_B_VALID=1 / WAIT_AW_READY=2 / WAIT_LAST_W_READY=3；`a2m`：IDLE=0 / READ=1 / WRITE=2 / SEND_B=3 / WAIT_WVALID=4。）

## 2. 改动

`rtl/soc/my_soc_top.sv` 的 `AXI_XBAR_CFG`：

```diff
-      FallThrough:        1'b0,
+      FallThrough:        1'b1,
       LatencyMode:        axi_pkg::NO_LATENCY,
```

- 只改一个参数，不动 `axi_mux`/`axi2mem`/`my_mainmem`，不屏蔽任何 AXI 事务。
- 顺带对 CPU 取指/访存、DMA 读写同样省去每个事务的一拍仲裁延迟（CPU 自检 3,659 → 3,650 拍）。
- 代价：W 通道路由由寄存器变为组合直通，端到端组合路径变长，必须重新综合→布局布线→STA 确认 20 ns 仍收敛。

## 3. 结果（RTL 级，行为级 SRAM，10 ns 时钟）

两套测试台跑同一份 `firmware.hex`：

- `tb_serial.sv`：一次一笔、等响应再发下一笔，与真实 DM SBA 及后仿 `write_word` 协议一致；
- `tb_lat.sv`：流水发射，测无损吞吐上限。

| 指标 | 串行 tb 基线 | 串行 tb + FallThrough | 流水 tb 基线 | 流水 tb + FallThrough |
| --- | ---: | ---: | ---: | ---: |
| 装载窗口 ACTIVE_START→CPU_WAIT_START | 82,360 ns / 8,236 拍 | 61,820 ns / 6,182 拍 | 62,030 ns / 6,190 拍 | 41,360 ns / 4,136 拍 |
| 每字拍数 | 4.01 | **3.01** | 3.01 | **2.01** |
| 端到端到 PASS | 118,950 ns / 11,895 拍 | 98,320 ns / 9,832 拍 | 98,490 ns / 9,849 拍 | 77,860 ns / 7,786 拍 |
| CPU 自检循环 | 3,659 | 3,650 | 3,659 | 3,650 |
| DMA 读/写与 MAC 重叠 | 62 / 93 | 62 / 93 | 62 / 93 | 62 / 93 |
| 功能 | PASS | PASS | PASS | PASS |

装载窗口：**−2,054 拍（−24.9%）**；端到端：**−2,063 拍（−17.3%）**。串行与流水两种协议下的绝对节省相同，说明省下的是每笔事务的固定一拍，而不是靠测试台灌水。

## 4. 物理实现与后仿确认

改动后重跑了完整流程（物理上传 `20261104_164956_2714f61`，后仿上传 `20261104_175010_postsim_2714f61`），34 步与三阶段全部通过：

| 项目 | 基线 43f5e38 | FallThrough 版 |
| --- | ---: | ---: |
| Setup / Hold WNS（20 ns） | +0.473 / +0.017 ns | **+0.257 / +0.020 ns** |
| 违规路径 / DRV | 0 / 0 | 0 / 0 |
| DRC / 天线 | 0 / 0 | 0 / 0 |
| 综合单元面积 | 1,895,736 µm² | 1,896,368 µm²（+0.03%） |
| 含 PAD 整 die | 3.795639 mm² | **3.795639 mm²**（上限 3.8） |

SDF 后仿（17 组：`sdf_max` + `gate_zero` + 15 个固件种子，含 16 组 SDF）结果：

| 项目 | 基线 | FallThrough 版 | 变化 |
| --- | ---: | ---: | ---: |
| 装载窗口 ACTIVE_START→CPU_WAIT_START | 600→165,320 ns（8,236 拍） | 600→124,240 ns（**6,182 拍**） | **−2,054 拍** |
| 到 FUNCTIONAL_PASS | 238,840 ns（11,912 拍） | 197,580 ns（**9,849 拍**） | **−2,063 拍（−17.3%）** |
| 到 POSTSIM_DONE | 238,920 ns | 197,660 ns | −2,063 拍 |
| CPU 自检 / NPU | 3,660 / 1,035 | 3,651 / 1,037 | 略微 |
| 重叠（读/写） | 62 / 93 | 62 / 93 | 0 |
| 功能 | 16/16 PASS | **17/17 PASS** | — |

后仿实测装载 6,182 拍、端到端 9,849 拍，与 RTL 级预测（6,182 / 9,832）逐拍吻合，说明省下的确实是网表行为而不是测试台假象。

时序消息：每组 SDF 在复位/时钟启动相位有 12 条 `$setuphold`（基线网表 11 条），站点集合不同（本次为 `i_axi2npu`/`i_dm_axi2mem`/`i_axi2boot`/`i_bootram` 的 ICG 与 `i_mainmem.port_wdata_q`），另有两组在末次复位再拉低时各 1–4 条。`audit.json` 判定 `active_window_dynamic_timing_clean: true`，工作窗口内 0 条；负 IOPATH 截零 8 处，未屏蔽任何检查。

若测试台同时采用流水装载（`eda/results/lat_stream_20261104`），两级收益可叠加：每字 4 拍 → 2 拍，装载 8,236 → 4,136 拍，后仿端到端约 7,786 拍。

## 5. 试过但无效的改动

`axi2mem` 的 `SEND_B` 增加“B 握手同拍接受下一笔单词写”的快路径（`eda/experiments/lat_rtl_20261104/axi2mem.sv`）：串行与流水两种装载实测周期数**完全不变**。原因是 DM 适配器在 `WAIT_B_VALID` 期间不会发出新的 AW/W，`SEND_B` 同拍根本没有下一笔可接。该改动未采纳。

## 6. 文件

- `tb_serial.sv`：串行装载台（与后仿同协议），含 4 个时间标记与 PASS 检查；
- `tb_lat.sv`：流水装载台；
- `tb_probe.sv`：逐拍探针台，用于定位 AW/W 分拍；
- RTL 改动见 `rtl/soc/my_soc_top.sv` 的 `AXI_XBAR_CFG`。
