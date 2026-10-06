[English](README.md) | [简体中文](README_CN.md)

对 `fulladd.brd` 使用 Allegro 命令行布局器，将结果保存为任务输出目录中的 `fulladd_placed.brd`。最终布局报告为 `placement.csv`，列为 `refdes,x_mm,y_mm,side,rot`。

1. 将输入板复制到可写目录。
2. 执行 `placement fulladd.brd fulladd_placed.brd`。
3. 从布局后的板导出 `placement.csv`。
4. 提交 `fulladd_placed.brd` 和 `placement.csv`。
