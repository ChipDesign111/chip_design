# 本地EDA结果

服务器版本：`/home/s2400012831/Desktop/fullstack_chipdesign/uploads/20261104_230714_2714f61`

压缩包、逐文件及34步输入身份已核对；大型GDS/DEF/SDF/SPEF与数据库保留服务器。

- [逐步运行报告](core/evidence/运行报告.md)：每步做什么、为什么和实际输出。
- [最终时序与物理检查](core/evidence/step_33.json)：Setup/Hold、DRV、DRC、供电、信号与天线。
- [最终导出检查](core/evidence/step_34.json)：DEF、SDF、SPEF与GDS结构对应关系。
- [布局图](core/evidence/34_final_layout.gif)。
- [原始综合报告](core/syn/my_soc_top/reports/)。
- [原始后端报告](core/pnr/my_soc_top/reports/)。
- [大文件服务器位置与SHA](review_manifest.json)。

解读方法见仓库eda/docs/报告查找与分析.md。压缩文本报告用gzip读取或先解压，时间单位为ns。独立晶圆厂签核和SDF回标仿真不在本流程结果中。

含 PAD 的整个 Die：3.7956390976 mm²，上限 3.8 mm²。
