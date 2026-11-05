# 后仿装载延时实验：流水式 SBA 写（2026-11-04）

同一份 43f5e38 网表与 SDF（物理上传 `20261029_43f5e38_sram_reset`），只把测试台的镜像装载从“一笔一答”改成流水发射，测量端到端周期变化。不修改 RTL、不改 SDF、不屏蔽时序消息。

## 1. 改动

`tb_postsim.sv` 原来的 `write_word` 每笔事务都要等 `r_valid` 才发下一笔，两个 `@(negedge clk)` 之间空一拍，实测固定 **4.0 拍/字**。实验版 `tb_postsim_stream.sv` 增加 `stream_image`：

- 发下一笔的地址只在上一次 `gnt` 之后的 negedge 更新，保证同一笔不会被重复接受；
- 不等写响应；响应由 `always @(posedge clk) if (dm_master_r_valid) resp_count++` 计数；
- 仍保持原有的保护检查：密钥单独写、部分镜像提交、错误密钥、CPU 不得抢跑；
- 写路径不变：DM master → `axi_adapter` → xbar → `axi2mem` → `my_mainmem` → SRAM。

## 2. 结果

| 项目 | 原始 tb | 流水 tb | 变化 |
| --- | ---: | ---: | ---: |
| 装载窗口（ACTIVE_START→CPU_WAIT_START） | 164,720 ns / 8,236 拍 | 123,800 ns / 6,190 拍 | **−2,046 拍** |
| 每字拍数 | 4.00 | 3.00 | −25% |
| 端到端（到 FUNCTIONAL_PASS） | 238,840 ns / 11,942 拍 | 197,920 ns / 9,896 拍 | **−2,046 拍（−17.1%）** |
| CPU 自检循环 | 3,660 | 3,660 | 0 |
| NPU / 重叠（93/62/93） | 1,035 | 1,035 | 0 |
| 动态时序消息 | 11 | 11 | 站点完全相同 |
| 功能 | PASS | PASS | — |

实测日志（`sdf_max`）：

```
LOAD_PARTIAL_ACK resp=35   time_ns=3020.000
LOAD_ISSUE_DONE  resp=2051 time_ns=124060.000
LOAD_RESP_DONE   resp=2052 time_ns=124080.000
CPU_WAIT_START           time_ns=124400.000
FUNCTIONAL_PASS cycles=3660 npu_cycles=1035 ... time_ns=197920.000
POSTSIM_DONE             time_ns=198000.000
```

`LOAD_ISSUE_DONE` 时响应已到 2051/2052，说明发射与返回速率持平，瓶颈在存储侧（`axi2mem` 单事务状态机 + `my_mainmem` 寄存端口），不在测试台。

## 3. 限制

- 这是**测试台吞吐优化**，不是硬件行为：真实 `dm_sba` 逐笔等待响应；流片后的 SBA 装载仍是 4 拍/字。
- 只跑了 seed 10000 的 `sdf_max` 与 `gate_zero`，未跑 16 组矩阵；`gate_zero` 仍因已知的 NPU `loading_bank` 竞争停在 CPU 自检。
- 时序消息数量与站点和基线逐一相同（7 个 ICG + 4 个 `i_axi2sram.\ax_req_q_reg[addr]`），没有新增。
- 继续降低需要改 RTL：`axi2mem` 支持 burst 或多笔在途，预计装载可到 2,600–4,100 拍，端到端再省 2,000–3,600 拍，但需重新综合→布局布线→17 组后仿。
