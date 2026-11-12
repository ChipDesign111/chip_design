# Lab5 全流程实测结果（2026-11-12）

完整源包整体部署，本轮只执行Lab5，绑定物理源码07af846。Lab5程序提交为aefa35686512a1aeaa9fbe2004a2915561e461c3。
所有新增阶段已执行完成，**整体尚未通过：Wire Bond仍有9条真实违规**。没有把课程例外扩展到WB。

| 项目 | 本轮结果 |
| --- | --- |
| 源码/物理输入 | 完整部署204项（含清单）；RTL与07物理输入匹配，611个GDS结构无缺失引用，原输入SHA未变 |
| CDL | 原生V2LVS完成，使用原STD/IO SPI及SRAM CDL；不是以空SRAM接口代替电路比较 |
| Seal Ring / POC | 原生1µm edge/corner装配，7836 edge+4 corner；POC位于实际M3轨 |
| 最终几何DRC | 523项检查；原始2426层次/14515展开，课程DRM/ESD/MOM/LUP四类以外0违规 |
| LVS | CORRECT；完整605项属性，PR3.48%基于42个3.47%实测差异；Split Gate YES，无新增SRAM Box/虚连 |
| ERC | 7层次/977展开；核对到PVDD1CDG/PVDD2CDG/PVSS1CDG及外环衬底，按教程保留，不写ERC Clean |
| 最终天线 | 62项检查、0违规 |
| Wire Bond | 64项检查，CB.S.2.M5有3处、CB.S.2.M6有6处，未豁免 |

原始Die（含PAD）1948.24µm见方、3.7956390976mm²。加入Seal Ring后的外框1979µm见方、3.916441mm²，符合教程1980µm外框上限；两种面积分开报告。
原生GDS为2000DBU/µm；项目私有技术库同步2000，原DRC5nm网格及LVS1nm解析分辨率保留，共享PDK不变。

## 修复及剩余项

已依据原始标记核对PVDD2CDG和PVDD2POC的CONT/PIMP/NIMP边界，只在项目私有版图扩展PIMP，CO.R.4归零。
M6原生填充后密度28.38%低于原30%要求；调整普通M6填充排布，大填充间距2.0→1.5µm，原工艺DRC阈值不变，最终M6.R.1归零。
WB9处已与原始Innovus GDS逐点比对，两个规则的标记集合完全一致，均在底边PAD附近。它们不是Seal Ring或Dummy引入的问题。
这9处需要回到受维护的PNR流程做PAD金属避让/布线修复，重新导出并验证，不能在Lab5删功能金属或关闭WB规则。本轮按要求没有重新运行前段。

## 来源及查看

- [结果数据](summary.json)
- [逐点WB及ERC对象检查](native_inspection.json)
- [原始报告校验清单](report_provenance.json)
- [首次定位依据](diagnosis.json)

服务器本轮目录：`/home/s2400011041/Desktop/fullstack_chipdesign/uploads/20261112_210755_lab5_aefa356`，其`soc-stu/layout`保存项目私有工作环境，`lab5/evidence`保存原生工具日志和摘要。
本地工作区`lab5/lab5_aefa356_final_20261112`已核验62个回传文件，SHA为`b9d2e20e6aa5acf1e989129966535f301032503f926ce47346af719a1af70ea5`；完整原文和授权大文件分别保留本地包/服务器，不把PDK规则和模型提交Git。
原始物理输入和最终GDS分别有SHA，最终GDS为`d9ce2df098a80ffb469064e53c7ad3b7d79773fbdef01cd903c8f72e05cd311b`。

2026-11-12只读观察远端main为6e76b77，已有另外的RTL优化；本轮结果不能证明该新版main通过Lab5。本任务没有改动main。
现有TT SDF属于原Innovus实现，不宣称做过Dummy后重新提取/STA、IR/EM或正式投片签核。
