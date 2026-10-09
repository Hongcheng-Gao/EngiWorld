[English](README.txt) | [简体中文](README_CN.txt)

# 在 AGND 与 DGND 之间添加零欧姆连接

打开 `mixed.sch`，其中 C1/C2 连接 AGND，R1/R2 连接 DGND。添加名为 `R_TIE` 的 0 Ω 电阻，使用 rcl.lbr 的 deviceset `R-EU_`、device/package `R0402`，将引脚 1 连到 AGND、引脚 2 连到 DGND，形成单个受控接地点，保存为 `tied.sch`。

评分检查：XML 正确；parts 中有 R_TIE；AGND/DGND 分别含该元件的 pinref 1/2；保留 C1/C2 与 AGND、R1/R2 与 DGND 的连接；两个地网络保持为独立 net。

`mixed.sch` 是四元件、双地网的初始原理图；`rcl.lbr` 用于加载电阻。典型命令：

```text
USE rcl.lbr;
ADD R-EU_R0402@rcl 'R_TIE' (90 40);
VALUE R_TIE 0R;
NAME AGND (85 40);
NAME DGND (95 40);
WRITE tied.sch;
```

引脚 1/2 位于放置点 x±5.08、相同 y。具体坐标可变化，评分只检查 XML 结构。
