# 整数参考模型

计划实现与 [数值规则](../../docs/numerics.md) 一致的两层网络，导出 hidden、scores、class。
RTL 对照该模型逐值比较；需要明确合法范围、舍入、饱和和 Argmax 平局规则。
