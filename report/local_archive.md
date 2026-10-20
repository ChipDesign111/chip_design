# 仓库外的本地归档管理

旧版不保留在当前分支的common/baseline或兼容测试目录中。本机归档位于 `advanced_chip_study/local_archive/chip_design/2026-10-20-before-final-only/`，与开发仓库及其worktree平级隔离，不上传GitHub。

| 内容 | 文件/目录 |
| --- | --- |
| 整理前完整公开源码 | source/，基线提交e20ba50413c35857d53ee04cbbfb218f105651b6 |
| 原始源码包 | source.tar |
| Git历史与分支备份 | history.bundle，已校验 |
| 每个文件和归档包SHA-256 | catalog.json |
| 本次移除文件索引 | removed_from_branch.json |
| 旧仿真运行产物 | runtime/ |
| 恢复与复测方法 | 归档README.md；上一级README.md提供版本索引 |

需要复测时从history.bundle克隆到新的replay目录，再切到基线提交；不要直接修改source快照。授权SRAM模型不包含在源码归档中，需另行配置。当前工程的unit/soc/synth均不读取这些旧文件，也不要求克隆完整Git历史。
