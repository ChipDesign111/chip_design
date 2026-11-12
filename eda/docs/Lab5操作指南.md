# Lab5：完整工程部署、仅执行新增物理检查

完整源包始终包含 RTL、综合、Innovus 01–34、TT 后仿和 Lab5 程序。workflow.json 定义各阶段必备文件，打包时逐项检查并记录 SHA；文件齐全不代表检查通过。

## 一键运行

```powershell
python eda/signoff.py run --eda-upload /home/s2400011041/Desktop/fullstack_chipdesign/uploads/20261029_150649_07af846 --output C:/Users/zixiang/OneDrive/Desktop/advanced_chip_study/lab5/本次新目录
```

完整上传、公共unpack.sh校验解压后，只启动Lab5，不调用原run_all.sh重跑综合和布局布线。
run --detach只启动；status查状态；fetch --wait --output 新目录等待并校验回传。
--upload显式选择Lab5版本，eda/dist/last_lab5.json只保存本地最近位置。

## 本地/服务器分工

本地仓库维护正式程序、配置和文档；eda/dist保存忽略的部署包；工作区lab5保存核验后小报告；开发试验只在archives。
服务器每轮独立建立uploads/时间_lab5_提交/soc-stu/layout，从/lec/lab5/layout复制课程工程并记录所有原文件SHA。
deploy为完整冻结源码；lab5/config.json为冻结配置；lab5/inputs为原物理输入副本；lab5/evidence为命令、原始日志、摘要和SHA。
soc-stu/layout/workspace保存私有OA、GDS及检查数据库；results保存结果和回传包。原物理work及共享PDK保持只读。
规则、授权模型、大GDS/CDL、OA、SVDB不入Git。物理源码提交与本轮程序提交分别记录。

## 执行和真实结果

核对物理34步/三阶段0、相同RTL、完整包SHA、GDS层次，执行原生V2LVS。
随后私有preDummy装配、OA导入、preDummy DRC、两种Dummy、合并、最终OA导入、DRC、LVS/ERC、天线及WB串行执行。
几何自动化读取原生GDS中的edge/corner按1µm节距装配，不缩放、不flatten功能子层次，记录原生子单元元素计数。
按DEF测量尺寸并单列最终含环外框；POC锚点需在实际PVDD2CDG M3导体内。实现及解析必须经实际工具运行验证。
服务器依赖项目tools/lab5_python中的Python3.12、gdstk0.9.61、numpy2.2.6；原生Calibre/Virtuoso环境照常使用。
家目录含运行环境和预计产物须低于20,000,000,000字节，重任务串行，保留最新有效物理与TT结果。

## 教学例外

依据 https://full-stack-ai-chip.tianyuj.com/lab-5/ 保留原始DRC报告，单列DRM/ESD/MOM/LUP四类。
ERC不能按名字全部忽略，需核对实际IO保护电路或外环对象；核心浮井、真实开短路须修复。
PR先保留原始容差，确认实测偏差与教程同类后才采用有依据的教学设置。不新增SRAM Box、虚连或假标签。
converted、executed_review_required、review_required均非通过。报告解析不完整、几何需修正或ERC未审阅均非零退出并回传依据。
最终检查绑定同一SHA最终GDS/CDL。Dummy后寄生/STA、IR/EM及封装人工规则未做分别列未做。

## 回传

成功或失败均生成小包；本地校验包及逐文件SHA生成receipt.json。代码/配置修改必须新部署，不覆盖冻结任务。
最终验收后清理可再生成临时文件；结果说明更新eda/results及服务器入口，只推送xzx、不自动合并main。
