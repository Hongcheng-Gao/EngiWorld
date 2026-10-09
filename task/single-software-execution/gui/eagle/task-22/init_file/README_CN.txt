[English](README.txt) | [简体中文](README_CN.txt)

# assign.sch 网络类别整理方案

使用原理图中已有的网络类别：

```text
SIG: class 1
PWR: class 2
HSPEED: class 3
```

按以下方式分配网络，并将原理图保存为 `answer.sch`：

```text
VCC -> PWR
GND -> PWR
CLK -> HSPEED
DATA -> HSPEED
RESET -> SIG
```
