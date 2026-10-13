# 选定 Lab 3 外围

来源：用户提供的 lab3-ST/SoC_cv32e40p，已完成四端口 NPU 接入的版本。按本次要求冻结这份外围，不声称它就是未经修改的官方发行包。

导入 CPU、AXI、Debug、复位/时钟、Boot RAM、8 KB 主 SRAM、my_soc_top、my_npu_subsystem 及头文件。选定原测试、C/hex、启动/链接、filelist 分别放入 verification/lab3/、sw/startup/lab3/、filelists/。

[manifest.json](manifest.json) 记录全部 90 个选定文件的来源相对路径和原字节 SHA-256。运行 python scripts/check_platform.py 验证。原版权/许可证头保留，Git 不转换行尾；没有为第三方代码添加新的统一许可证。

原 NPU 未作为外围导入，团队两个实现位于 rtl/npu/lab3/、har/。这里没有 PDK、商业工具、标准单元库、个人报告或产物。来源和使用范围见 [sources.md](../../docs/sources.md)。
