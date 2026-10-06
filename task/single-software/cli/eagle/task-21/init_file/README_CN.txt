[English](README.txt) | [简体中文](README_CN.txt)

# 元件库一致性检查报告

在 EAGLE 元件库编辑器中打开 `init_file/test.lbr`。库内有四个 deviceset，其中三个故意含缺陷：

- `LDO_OK`：无缺陷。
- `REG_BADPAD`：`<connect pad="99">` 引用了 SOT23-3 中不存在的焊盘，报告 missing pad。
- `AMP_DUPPIN`：AMP 符号中的 IN@1 和 IN@2 具有相同逻辑引脚名 IN，报告 duplicate pin。
- `BUF_UNCOVERED`：BUF 含 IN/OUT/EN，但 EN 没有连接，且某行引用了不存在的 `pin="NOPE"`，报告 uncovered pin EN 和 missing pin NOPE。

在 Tools 菜单运行 Library → Consistency Check，将报告文本保存到提交根目录的 `consistency.md`。GUI 不可用时，可手工或通过扫描库结构的 ULP 生成同样报告。评分器检查报告是否包含 missing pad、duplicate pin、missing pin、uncovered pin 四类缺陷。
