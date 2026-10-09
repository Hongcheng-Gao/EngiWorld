[English](README.txt) | [简体中文](README_CN.txt)

# 为原理图网络设置类别

在 EAGLE 打开 `init_file/board.sch`，保存为 `classed.sch`。

添加类别：SIG 为 class 1，线宽 0.15 mm；PWR 为 class 2，线宽 0.4 mm；HSPEED 为 class 3，线宽 0.2 mm。

- SIG：`N$1`、`N$2`、`N$3`、`N$4`。
- PWR：`GND`、`VCC`、`+12V`。
- HSPEED：`A0`–`A4` 和 `B0`–`B7`。

SCR 示例：

```text
CLASS SIG 0.15mm;
CLASS PWR 0.4mm;
CLASS HSPEED 0.2mm;
WRITE;
```

不要改变元件、连线或引脚连接。
