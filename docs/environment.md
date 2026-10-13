# Tooling and quick start

## 依赖

| 工作流 | 依赖 |
| --- | --- |
| 仓库检查 | Python 3.11+ |
| RTL / MMIO | Icarus Verilog、vvp |
| 真实模型 | 上述工具 + `requirements.txt` 中的 NumPy |
| 完整 SoC | ModelSim，及有效的本地工具许可证 |
| 通用结构检查 | Yosys |

训练依赖 Torch、NumPy、scikit-learn，参见 [训练文档](../model/training/README.md)；验证已有导出权重不需要 Torch 或 checkpoint 反序列化。

Linux CI 安装 Icarus/Yosys；Windows 已验证 Icarus 11、ModelSim 2019.2 和通用 Yosys。Python 依赖按 [requirements.txt](../requirements.txt) 锁定。

## 环境诊断

```sh
python -m pip install -r requirements.txt
python project.py doctor
python project.py doctor --require unit --require model --require synthesis
```

doctor 只检查，不安装软件或修改环境。它区分可选工具缺失与所选工作流的必需依赖；输出不会包含许可证内容。许可证配置不等于已验证许可证有效。

可执行文件从 PATH 查找，或通过 `--iverilog`、`--vvp`、`--vsim`、`--yosys` 指定。所有命令定位仓库根目录，支持从其他当前目录调用。

## 标准命令

```sh
python project.py check
python project.py test --suite unit --count 12
python project.py test --suite unit
python project.py test --suite model
python project.py synth
python project.py ci
```

12 组合成用例用于调试；完整 unit 默认 1000 组（3000 推理）。model 使用 24 条真实固定输入（单/双模式共 48 推理）。ci 复现公共 CI 的检查集合，不包含商业 SoC 仿真。

```sh
python project.py test --suite soc --vsim /path/to/vsim
python project.py test --suite model-soc --vsim /path/to/vsim
python project.py test --suite all --vsim /path/to/vsim
```

`all` 包含 unit、model、soc、model-soc。完整 AXI SoC 包含 SystemVerilog interface，使用 ModelSim；Icarus 单元测试不替代 SoC 仿真。

## 全量真实数据

```sh
python project.py download-data
python project.py test --suite model-soc --data-root "data/UCI HAR Dataset" --vsim /path/to/vsim
```

使用官方测试集全部 2947 条做模型/RTL 对照，CPU 自检仍采用六类各 4 条。来源和具体判定见 [模型验证](model-verification.md)。原始数据保留在忽略的 `data/`。

## 许可证与产物

ModelSim 优先使用环境变量 `LM_LICENSE_FILE`；未设置时后端尝试安装目录上一级的 LICENSE.TXT。其他布局由本地环境配置。不提交许可证或工具数据库。

| 路径 | 产物 |
| --- | --- |
| `build/unit/`、`build/vectors/` | Icarus 镜像、合成向量 |
| `build/soc/{lab3,har,har-model}/` | 独立 work、Tcl、仿真数据库 |
| `build/real_model/` | 真实向量、CPU 镜像、准确率和结果 |
| `build/logs/`、`build/results/` | 回归日志、结构化结果 |
| `build/synthesis/` | 通用网表、结构检查日志和摘要 |

同一 checkout 不并发运行共用上述目录的回归。失败时先看首个失败阶段及对应日志；CPU $finish 的零退出码不代表 PASS，后端还会检查 SRAM magic。
