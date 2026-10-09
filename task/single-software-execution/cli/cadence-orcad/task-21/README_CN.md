[English](README.md) | [简体中文](README_CN.md)

# task-21

对 `init_file/fulladd.brd` 使用 Allegro 命令行布局器，将真实布局结果保存为 `output/fulladd_placed.brd`，导出 `output/placement.csv`，列为 `refdes,x_mm,y_mm,side,rot`。

1. 将 `fulladd.brd` 复制到可写工作目录。
2. 在该目录执行 `placement fulladd.brd fulladd_placed.brd`。
3. 将最终元件布局导出为 `placement.csv`。
4. 提交 Allegro 数据库和布局报告。
