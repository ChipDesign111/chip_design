# W8A4 连续流水 RTL 实测

日期：2026-10-20。基于52be8c5，新增可选CHIP_STREAM_NPU配置，保留FC1 32×4、FC2 6×2、32路重定标和INT8权重banks。原INT8默认配置继续可用。

## 公平对比结果

以下为24条真实HAR输入，同一W8A4模型、同一RTL、同一固件布局。三份固件只有MODE立即数所在的一条32 bit指令不同；代码均624 B，包含模型/输入/类别金标准的SRAM镜像使用3904 B。CPU经AXI装载参数并启动DMA/NPU，逐条读取并检查类别；测试台被动对比每条的全部32个hidden和6个score及类别，没有注入PASS。

| 指标 | MODE0 单条在途 | MODE1 间隔20 | MODE3 去空泡 | 20周期版→去空泡加速 |
| --- | ---: | ---: | ---: | ---: |
| 充分供数的NPU单元总周期 | 1153 | 509 | 417 | 1.221× |
| SoC内NPU窗口：ARM至末条结果 | 1389 | 633 | 548 | **1.155×** |
| 首条至末条结果跨度 | 1216 | 460 | 375 | **1.227×** |
| 实际相邻结果间隔 | 39～68 | 20 | **16～17** | — |
| CPU测量的流处理窗口 | 1500 | 736 | 696 | **1.057×** |
| 整机启动至CPU自检完成 | 4614 | 3850 | 3810 | **1.010×** |

两种SRAM后端portable-sram、RA1SHD的所有周期和数据计数完全一致。MODE0→MODE3的NPU窗口加速2.535×，整机加速1.211×；MODE0属于本版的单条在途模式，不是历史旧INT8实现。

去空泡改善了核心吞吐，但没有把整机加速到1.25×：整机时间含一次参数装载、CPU取指、CSR设置、轮询、类别自检和统计写入。CPU轮询与DMA共享单口SRAM，实际供数仍造成若干1周期停顿。不得把旧INT8固件包含大量hidden/score软件读取的历史36571周期直接除以3810来宣传加速，那同时改变了精度、批次调度和软件校验工作量。

## 利用率口径

两层每条各发射16组，24条各384个有效发射周期。按每层“首次至末次发射”的窗口计：

- MODE1：窗口476周期，384/476 = **80.67%**。
- MODE3：窗口391周期，384/391 = **98.21%**。
- 充分供数的单元测试MODE3严格每16周期出一条，连续帧内部无发射空泡。

该98.21%排除了各级开始前的等待和末次发射后的排空，不能称为整批/整机利用率。若把ARM至末条结果的548周期全部计入，每层384/548=70.07%。前者用于定位调度和供数空泡，后者包含批次启动与流水填充成本。

真实数据握手与计算发射同周期：MODE0为0、MODE1为154、MODE3为**187周期**。该计数只在AXI R或W握手且FC1/FC2有效发射时递增，证明发生真实传输/计算重叠；另一个dma_compute_overlap仅表示DMA busy与计算重叠，可能包括DMA等待信用，不能单独用作传输重叠证据。

所有模式均观察到790个读数据拍和790个写数据拍：598字参数+192字输入。R/W同时握手740周期。参数只装载一次，24条输入一次提交，16字突发通常包含两条32 B输入。

## 功能与兼容验证

- 24条真实样本×三种调度模式，全部32个hidden、6个score和类别逐值正确；两种SRAM后端完整CPU/SoC自检通过。
- 完整2947条官方测试样本，MODE3按最多64条分批，全部hidden/score/class与W8A4整数参考一致；每批连续结果间隔16周期。模型分类正确2490/2947，与硬件一致性是不同指标。
- 新DMA协议测试248个完成请求，包含200次随机搬运、独立AR/R/AW/W/B背压、7种错误情形、4KiB拆分、忙时冲突和4种在途复位。另检查流请求未ARM、源未32 B对齐、非整帧长度、暂存信用等待、1/2帧成功提交和错误突发不提交。
- 新NPU验证未提交/中止输入不进入计算、乱序暂存写报错、活动计算中复位后无残留结果。
- 原默认INT8回归：1000组/3000次推理、12项MMIO、SRAM、原DMA、真实模型单/双模式及原24条CPU/SoC程序均通过。
- 通用综合无锁存器。新NPU保持140路点积乘法、32路重定标，共172个通用乘法；权重17920 bit。DMA为512-bit FIFO、349 bit显式寄存器、无乘法器。NPU通用显式寄存器11227 bit，不含RAM内部同步读状态；不是目标工艺面积报告。

数值摘要：[results.json](results.json)。源身份：[source_manifest.json](source_manifest.json)。完整日志/仿真数据库保留在本地对应runs目录，不公开厂商文件或编译产物。全量RTL验证与最终SoC基准使用相同五个NPU/DMA源SHA；后续变动仅增加被动测试计数，不改变硬件。

## 复现与边界

```sh
python tools/project.py check
python tools/project.py test --suite stream-unit
python tools/project.py test --suite stream-unit --data-root "model/data/UCI HAR Dataset"
python tools/project.py test --suite stream --memory portable-sram --vsim /path/to/vsim
python tools/project.py test --suite stream --memory ra1shd --vsim /path/to/vsim
python test/2026-10-20/scripts/check_stream_synthesis.py --yosys /path/to/yosys
```

原数据需从官方UCI归档下载，model/data被忽略；固定24条gold随仓库提供。原checkpoint曾用官方测试集选择最佳模型，本次不是新盲测。授权本地SRAM采用功能仿真并关闭时序检查；未完成FPGA板级、目标频率、STA/SDF、面积/功耗或物理签核。每批最多64条，出现DMA错误后须弃用本批并全局复位；源数据在DMA完成前不得修改。

设计与MMIO详见 [streaming.md](../../../report/streaming.md)。
