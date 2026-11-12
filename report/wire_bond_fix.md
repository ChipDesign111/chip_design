# Wire Bond间距修复

基线07af846的WB规则CB.S.2.M5有3处、CB.S.2.M6有6处，要求PAD金属与附近其他金属至少2.5µm。
只读恢复原始最终DB查询发现标记附近是CPU普通布线，包括lsu_rdata、寄存器堆读数据和PC路径；不是通过关闭WB规则处理的例外。

正式修复在步骤10所有Bond PAD固定后，依据实际PAD实例box，在M5/M6创建原生信号布线避让对象并设置spacing=2.5µm。
不指定旧网名、不手工插缓冲/删金属，不改变PAD/PG/RTL/SDC；PG仅不受该信号布线障碍影响，最终WB对全部真实金属仍执行完整检查。
原生21.16预检已读回34个PAD、68个分层对象、isExceptPGNet=1、isPGNetOnly=0和spacing=2.5。
每次恢复后检查对象/层/属性仍在；真正通过必须以新完整实现和Calibre最终WB为准。预检没有保存旧DB。

一键启动本轮完整物理及TT/新Lab5链路：

```powershell
python eda/pipeline.py run --start-at implementation --output C:/Users/zixiang/OneDrive/Desktop/advanced_chip_study/lab5/本次新修复目录
```

`implementation`仍运行硬件来源检查并从全新Genus开始，不复用旧检查点，只省略未修改RTL的功能回归；新TT SDF仍完整运行。
结果通过后才更新最终报告并清理旧的相关服务器版本。新main的RTL与本分支基线不同，本任务不自动合并或改main。
