[English](README.txt) | [简体中文](README_CN.txt)

# DRC 回归检测

给定两个板修订版本 `before.kicad_pcb`、`after.kicad_pcb` 和 DRC 规则 `rules.kicad_dru`，最小间距为 0.2 mm。

1. 生成 `diff.json`，区分新增和已解决的违规。
2. 生成 `fixed.kicad_pcb`，只修复新增违规，保留 after 版本中的其他编辑。

输出为 `output/diff.json` 和 `output/fixed.kicad_pcb`。
