[English](README.md) | [简体中文](README_CN.md)

## NREL 5 MW ROSCO 增益调度研究

`DISCON.IN` 是使用 ROSCO 2.10.1 生成的 NREL 5 MW 控制器输入文件。
`libdiscon.so` 根据官方 ROSCO v2.10.5 标签为 x86-64 Linux 编译：

https://github.com/NatLabRockies/ROSCO/tree/v2.10.5

所需的转子性能表来自该标签中的官方 NREL 5 MW 数据：

https://raw.githubusercontent.com/NatLabRockies/ROSCO/v2.10.5/Examples/Test_Cases/NREL-5MW/Cp_Ct_Cq.NREL5MW.txt

SHA-256 校验值：

```text
45111ec68ce797c9c6f6d0352642f1ebeff2315cff187a846ae1660c780dbfcf  libdiscon.so
a8d9c2d88bd1d9073287256b042d7752d2202a01e611c08e283b9109504caf5b  Cp_Ct_Cq.NREL5MW.txt
```
