[English](README.md) | [简体中文](README_CN.md)

为 `demo.brd` 生成真实的 Allegro Gerber 光绘文件集。

所需文件：

- `TOP.art`
- `BOTTOM.art`
- `POWER.art`
- `GND.art`
- `photoplot.log`

典型流程：

1. 将 `demo.brd` 和 `art_param.txt` 复制到同一个可写工作目录。
2. 执行 `artwork demo.brd`。
3. 收集并提交上述五个输出文件。
