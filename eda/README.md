# 当前EDA流程

正式入口为pipeline.py，依次执行来源检查/功能回归、Genus、34步Innovus、TT门级后仿、同DB SRAM STA和Lab5。每轮独立上传并冻结输入，不覆盖历史数据库。

```powershell
python eda/pipeline.py run --postsim-firmware-dir report/results/optimized_functional/postsim_payloads --output C:/Users/zixiang/OneDrive/Desktop/advanced_chip_study/lab5/soc_new_run
```

输出目录必须不存在或为空。新增RTL需完整功能回归；显式`--start-at implementation`只省略未修改RTL的回归，仍做来源检查并重新综合实现。已完成的同源功能结果可经`--rtl-regression-result`校验完整源码SHA后复用。

| 工具 | 用途 |
| --- | --- |
| remote.py | 打包、部署、环境准备、综合/实现、状态与核验回传 |
| postsim.py | 对已完成物理版执行独立SDF、同DB SRAM STA和回传 |
| signoff.py | 绑定已完成物理输入，只执行Lab5 |
| package_server.py / unpack.sh | 无授权模型源码包及服务器安全解包 |
| server/ | 正式配置、Tcl、环境检查、物理/后仿/Lab5工具 |

当前验收范围是20ns、TT、SI关闭和原生低RC配置；Setup/Hold须非负、TNS与负路径为0，保留原生模型、notifier和完整SDF检查。Lab5依次进行输入核对、CDL、封环/POC、DRC、填充、合并、LVS/ERC、天线和线焊检查。课程DRC/ERC例外须逐项保留，不称完整代工厂签核。

服务器chipdesign需要Genus/Innovus/VCS/Calibre及授权PDK/SRAM。Lab5的20GB上限和6GB峰值预留保持不变，启动前需核对空间。`eda/dist/`只保存本地生成包与上传指针，受.gitignore忽略；完整回传包放仓库外lab5目录，不能放进main当作另一份源码。

本版唯一结果入口为[当前验收](../report/results/README.md)，其中保留物理、后仿、Lab5三个服务器目录与输入SHA。细节参考[验收条件](docs/验收条件.md)、[34步说明](docs/讲义34步与文件对照.md)、[后仿操作](docs/后仿真操作指南.md)、[Lab5操作](docs/Lab5操作指南.md)。旧版结果见[历史入口](../report/history.md)。
