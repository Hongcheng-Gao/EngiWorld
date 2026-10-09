[English](README.txt) | [简体中文](README_CN.txt)

# LM324 四运算放大器：EAGLE 元件库制作要求

交付物：提交目录根目录下的 `lm324.lbr`。

LM324 是典型的 DIP-14 四运放：一个器件、一个符号、一个封装，包含四个电气特性相同的运放门单元 A/B/C/D，共用一对 V+ / V- 电源引脚。请为它制作完整的 EAGLE 元件库。

标准 DIP-14 引脚定义：

```text
  Pin  1  = Gate A  OUT
  Pin  2  = Gate A  IN-
  Pin  3  = Gate A  IN+
  Pin  4  =         V+
  Pin  5  = Gate B  IN+
  Pin  6  = Gate B  IN-
  Pin  7  = Gate B  OUT
  Pin  8  = Gate C  OUT
  Pin  9  = Gate C  IN-
  Pin 10  = Gate C  IN+
  Pin 11  =         V-
  Pin 12  = Gate D  IN+
  Pin 13  = Gate D  IN-
  Pin 14  = Gate D  OUT
```

元件库结构要求：

- `<package name="DIP-14">` 包含 14 个通孔 `<pad>`，名称为 `1` 至 `14`，采用标准 2.54 mm 脚距，排距约 7.62 mm 即可。
- `<symbol name="OPAMP">` 恰好包含 IN+、IN-、OUT、V+、V- 五个引脚。
- `<deviceset prefix="U">` 包含四个 `<gate>`，名称分别为 A、B、C、D，均使用 `symbol="OPAMP"` 和 `swaplevel="1"`。后者使 ERC 允许四个电气特性相同的运放门相互交换。
- 唯一的 `<device package="DIP-14">` 内包含 `<connects>`，给出每组门、引脚和焊盘的映射：

```text
A/IN- -> 2   A/IN+ -> 3   A/OUT -> 1   A/V+ -> 4  A/V- -> 11
B/IN- -> 6   B/IN+ -> 5   B/OUT -> 7   B/V+ -> 4  B/V- -> 11
C/IN- -> 9   C/IN+ -> 10  C/OUT -> 8   C/V+ -> 4  C/V- -> 11
D/IN- -> 13  D/IN+ -> 12  D/OUT -> 14  D/V+ -> 4  D/V- -> 11
```

每个门的 V+ 都连接焊盘 4，V- 都连接焊盘 11，以表示共享电源。

评分器只检查 XML 结构，不会在 EAGLE 中打开文件。文件能解析为 XML 并满足上述结构即可通过：14 个焊盘的封装、5 个引脚的符号、4 个均设置 `swaplevel="1"` 的门，以及正确的门—引脚—焊盘映射。
