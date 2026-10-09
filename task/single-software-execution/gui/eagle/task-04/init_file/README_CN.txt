[English](README.txt) | [简体中文](README_CN.txt)

# 从零制作 EAGLE XC6206 元件库

交付 `mylib_xc6206.lbr`，表示 SOT-23-3 封装的三端 XC6206 类 LDO。

1. PCB `<package>` 名称包含 `SOT`，如 `SOT23` 或 `SOT23-3`，包含名称为 1、2、3 的三个 SMD 焊盘。参考几何（mm）：

```text
pad 1: x=-0.95 y=-1.10 dx=1.0 dy=1.4
pad 2: x=+0.95 y=-1.10 dx=1.0 dy=1.4
pad 3: x= 0.00 y=+1.10 dx=1.0 dy=1.4
```

在 21 层 tPlace 或 51 层 tDocu 至少放一个轮廓元素，并通过焊盘 1 附近的小图形或 tPlace/tNames 的文字 `1` 标识首脚。

2. 一个 `<symbol>`，恰有 VIN（in/pas）、GND（pwr/sup）、VOUT（out/pas）三个引脚。
3. `<deviceset prefix="U">` 通过单个 gate 和 device 将符号与封装绑定，并用 connects 映射引脚。真实 XC6206 对应 VIN→1、GND→2、VOUT→3。评分器接受每个引脚名恰好出现一次的连接布局。

文件需能被 Python `xml.etree.ElementTree` 解析；可以包含 EAGLE DOCTYPE。

原参考封装位于 `/zfspool/zangyihe/eagle/eagle-7.7.0/lbr/ref-packages.lbr` 的 SOT23 项，可补充第三个焊盘形成 SOT-23-3。
