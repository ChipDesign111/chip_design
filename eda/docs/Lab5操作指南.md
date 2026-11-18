# 当前Lab5流程

Lab5绑定已完成34步的同一物理输入，使用完整源码包但只执行物理后处理和检查。

```powershell
python eda/pipeline.py run --only lab5 --eda-upload /home/s2400011041/Desktop/fullstack_chipdesign/uploads/本轮物理目录 --output C:/Users/zixiang/OneDrive/Desktop/advanced_chip_study/lab5/本轮Lab5
```

完整新流程见[EDA入口](../README.md)。当前物理目录和原始输入SHA从[本版验收记录](../../report/results/final_result.json)读取，不把示例中的旧版本号当默认目标。

流程依次核对原GDS/网表/DEF、v2lvs转CDL、生成封环/POC、导入OA、填充前DRC、金属及OD/PO填充、合并、填充后DRC、LVS/ERC、天线和Wire Bond。CDL成功不等于LVS通过；只有最终报告完成才更新状态。

每次使用私有工作副本和当前几何/规则。既有PAD PP修复只应用于私有副本，共享PDK和原物理输入保持不变。M6覆盖率在填充后实际检查，不能借旧密度结果代替。

DRC保留原始计数与课程排除项；ERC逐对象核对原生IO/外环残留，未知对象或进入核心的残留不能直接豁免。当前结果是LVS正确、DRC原始2426/非课程排除0、ERC 7层次/977展开且Clean=false、天线62项和Wire Bond64项均0违规。它是课程验收，不是完整代工厂签核。

20GB空间上限与6GB峰值预留不变；启动前现有占用须满足预算。存储检查失败时先做可核验归档，再新建独立Lab5运行，不降低门槛或改写失败日志。

```powershell
python eda/signoff.py status --upload /home/s2400011041/Desktop/fullstack_chipdesign/uploads/本轮Lab5目录
python eda/signoff.py fetch --upload /home/s2400011041/Desktop/fullstack_chipdesign/uploads/本轮Lab5目录 --output C:/Users/zixiang/OneDrive/Desktop/advanced_chip_study/lab5/本轮Lab5核验
```

回传包和逐文件SHA核验后保留在仓库外。main仅保留[当前结果](../../report/results/README.md)，历史版本由[归档入口](../../report/history.md)访问。
