# FPGA INT8 测试镜像

本目录保存完整的 2048×32-bit（8 KiB）自检镜像。每个 `.hex` 文件包含
RV32I 自检程序、权重、偏置、输入、整数 golden 和 PASS/FAIL 回写逻辑，
每行一个 8 位十六进制 32 位字。

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

`int8_selftest.hex` 保留原来的 CRLF 字节格式和 SHA-256：

```text
fa38f91311768cd73386f8e093370831383d9e0e1b8a4832a2f3f978a2bfe850
```

`int8_uci_00_batch4.hex` 与其 2048 个字内容相同，但使用 LF 换行，因此二者
文件 SHA 不同。后续新镜像均使用 LF 换行和 18,432 B 文本大小；canonical
保持 20,480 B，以避免改变已测试 bitstream 的固件身份。

`image_manifest.json` 是权威清单，记录每个文件的 seed、batch 和 SHA-256。

## 测试内容

每个镜像运行相同的 RV32I 自检流程：

1. 配置 W1/W2 基址、batch 和 requant 参数。
2. 将 FC1/FC2 bias 和所有样本输入复制到 NPU MMIO。
3. 启动 NPU，检查最终状态严格为 `done=1, busy=0, error=0`。
4. 对每个样本逐项比较 packed hidden、6 个 INT32 score 和 class。
5. 检查 tile 加载数、FC1 相位周期和 FC2 相位周期。
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
- UCI 00 与既有 canonical 镜像的 2048 个字完全一致。

脚本不会覆盖已存在的 `int8_selftest.hex`；若它缺失，则用 UCI 00 创建。

## 板上使用

预装载 bitstream 在 FPGA 配置时只装入 `FPGA_INIT_FILE` 指定的一个镜像。
要切换不同文件，应使用 `SRAM_INIT_FILE=""` 的无预装载 bitstream，并按
[../README.md](../README.md) 的 JTAG 流程加载。

每次切换镜像前复位 SoC。复位只清除 Boot 装载计数，不清空 SRAM；加载器
必须重写完整的 2048 字，包括未使用区和零值。
