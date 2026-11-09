# FPGA INT8 测试镜像

本目录保存完整的 2048×32-bit（8 KiB）自检镜像。每个 `.hex` 文件包含
RV32I 自检程序、权重、偏置、输入、整数 golden 和 PASS/FAIL 回写逻辑，
每行一个 8 位十六进制 32 位字。

2026-11-09 的活动镜像使用 `scheduled4` RV32I 固件：四字循环展开并调度独立
load/store，保留所有逐项结果和计数检查。38 个 seed 已在固定 RTL 的真实 CPU
仿真中验证；本次没有重新生成 FPGA bitstream，也没有重新上板测试。既有板测
结论仅对应 `fpga/versions/20261104_rtl-1c265c0_int22/` 的冻结版本。

## 镜像集合

| 文件 | seed | batch | 用途 |
|---|---:|---:|---|
| `int8_selftest.hex` | 10000 | 4 | 默认 canonical 镜像；UCI 00 |
| `int8_uci_00_batch4.hex` | 10000 | 4 | UCI 00，与 canonical 内容相同 |
| `int8_uci_01_batch4.hex` | 10001 | 4 | UCI 01 |
| `int8_uci_02_batch4.hex` | 10002 | 4 | UCI 02 |
| `int8_uci_03_batch4.hex` | 10003 | 4 | UCI 03 |
| `int8_uci_04_batch4.hex` | 10004 | 4 | UCI 04 |
| `int8_uci_05_batch4.hex` | 10005 | 4 | UCI 05 |
| `int8_random_00_batch4.hex` ... `int8_random_31_batch2.hex` | 0...31 | 按文件名 | 随机/边界回归 |

UCI 00–05 各包含 4 条连续输入，共覆盖固定模型的 24 条输入。32 个随机镜像
与 `test/int8/run.py` 的默认回归 seed 0–31 一一对应，覆盖 batch=1/2/4、
不同 requant 参数、MULT=0、bias 极值以及 W1 基址 `0x80000FFC`/`0x80001000`。

当前 `int8_selftest.hex` 与 UCI 00 使用相同的 LF 文本格式，大小为
18,432 B，SHA-256 为：

```text
d9b9eea1e5f104290fd8566ffa961a577680a0a1c272757281633b3404d4982d
```

`int8_uci_00_batch4.hex` 与 canonical 文件逐字节相同。上一版 20,480 B、
CRLF 格式的 canonical 镜像已随旧 FPGA 版本冻结，不再作为当前输入。

`image_manifest.json` 是权威清单，记录每个文件的 seed、batch、固件模式、代码
字节数和 SHA-256，以及生成器、汇编器、模型数据等来源文件的 SHA-256。
当前 canonical 的代码为 1388 B，8 KiB 小端 `int8_selftest.bin` 已同步；其
SHA-256 为 `728b03bc0591fc373753622fc7db063de0fa25cc331d184482cc3a2e2e2aabab`。
已有对应 hex 的 8 个活动 bin 均由 `../prepare_jtag_image.ps1` 转换。
`int8_partial_4k.bin` 保留为历史 fixture，不属于本轮生成或验证的镜像。
最近板测完整版本快照见
[20261104_rtl-1c265c0_int22](../versions/20261104_rtl-1c265c0_int22/README.md)。

## 测试内容

每个镜像运行相同的 RV32I 自检流程：

1. 配置 W1/W2 基址、batch 和 requant 参数。
2. 将 FC1/FC2 bias 和所有样本输入复制到 NPU MMIO。
3. 启动 NPU，检查最终状态严格为 `done=1, busy=0, error=0`。
4. 对每个样本逐项比较 packed hidden、6 个 INT32 score 和 class。
5. 检查 tile 加载数、FC1 和 FC2 的 issue 计数。
6. 成功写 `0xC0DEC0DE` 到 `0x80001FE0`，失败写 `0xDEADBEEF` 并停在自循环。

镜像验证的是硬件数值和调度结果与同一整数模型一致，不等于完整数据集准确率。

## 重新生成

从仓库根目录运行：

```powershell
python fpga/firmware/generate_images.py
```

脚本会生成 32 个随机镜像、6 个 UCI 镜像和 `image_manifest.json`，并校验：

- 每份镜像恰好 2048 个 32 位字；
- 文件名中的 batch 与输入数据一致；
- 刷新后的 UCI 00 与 canonical 镜像的 2048 个字完全一致。

脚本会用最新的 UCI 00 刷新 `int8_selftest.hex`。旧镜像保存在带日期的
`fpga/versions/` 目录中，不再通过保留活动 canonical 文件来保存历史身份。
此脚本只生成 hex 和清单；更新 hex 后，需要按 `../README.md` 的转换命令刷新
拟装载的 bin。

## 板上使用

预装载 bitstream 在 FPGA 配置时只装入 `FPGA_INIT_FILE` 指定的一个镜像。
要切换不同文件，应使用空 `SRAM_INIT_FILE` 的无预装载 bitstream，并按
[../README.md](../README.md) 的 JTAG 流程加载。

每次切换镜像前复位 SoC。复位只清除 Boot 装载计数，不清空 SRAM；加载器
必须重写完整的 2048 字，包括未使用区和零值。
