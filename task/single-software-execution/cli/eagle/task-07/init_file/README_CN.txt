[English](README.txt) | [简体中文](README_CN.txt)

# 在新元件库中创建 10 引脚 CONN10 符号

交付 `conn10.lbr`。

1. 在 EAGLE 使用 File → New → Library。
2. 通过 Edit → Symbol 新建 `CONN10`。
3. 使用 PIN 放置编号 1–10 的十个引脚，典型布局为左右各五个，网格 0.1 英寸（2.54 mm）。
4. 所有引脚设置 `direction="pas"`，即 PIN 默认的无源类型。
5. 在 94 层 Symbols 绘制矩形本体，在 95/96 层放置 `>NAME` / `>VALUE`。
6. 可选：用 `<deviceset>` 封装符号，使其能用于原理图。
7. 保存为 `conn10.lbr`。

评分检查：库中恰有一个名为 CONN10 的 `<symbol>`；恰有十个 `<pin>`，名称为字符串 `1`–`10`，且方向全部为 `pas`。
