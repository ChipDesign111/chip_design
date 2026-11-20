# EGo1接线照片与CPU JTAG复核

收到用户新增跳线和两张照片后重新探测。USB外接适配器仍已附加到WSL；重新配置冻结RAW bitstream成功。配置前读全1，重新配置后1 MHz、100 kHz及课程FTDI初始化的10 kHz均读全0，CPU TAP未识别。没有装载常驻固件，没有执行真实板上推理；所有临时OpenOCD探测均已shutdown。原始日志、课程参数测试配置和bitstream SHA见本目录。

照片可确认EGo1和课程同外观ALINX USB CABLE。具体两端针号/触点被线与角度遮挡，无法按颜色核对六根线。原五线说明遗漏VREF，已在[演示说明](../../fpga/demo/README.md)更正：TCK/TDI/TDO/TMS接J5的17/18/19/20，GND接33或34，VREF接35或36（3.3V）。该遗漏是说明错误，尚无证据确认用户实物缺VREF或它就是故障原因。

[课程Lab6第8.2节](https://full-stack-ai-chip.tianyuj.com/lab-6/)的下载器端面2×5插口定义：标签向上、正对插口，上排左→右TDI、空、TMS、TDO、TCK；下排GND、空、空、VREF、GND。不要将这张图的顺序用于外壳顶部长窗口。J5信号针号由[EGo1手册第14节](https://e-elements.readthedocs.io/zh/ego1_v2.2/EGo1.html)核对；电源/地脚见课程附图。

TAP复位需P15外部复位释放、MMCM锁定且经过两个系统时钟沿。当前仅凭静态LED照片无法证明心跳闪烁。用户需先确认VREF和六根跳线的端点；若连接正确，再排查复位/时钟。未修改RTL，未修改历史冻结版本，也没有新的ASIC签核结论。

SHA256.json覆盖本记录文件（不含索引自身）；不保存用户照片到仓库。
