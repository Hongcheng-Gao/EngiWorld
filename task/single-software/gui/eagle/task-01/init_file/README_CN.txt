[English](README.txt) | [简体中文](README_CN.txt)

# 555 非稳态 LED 闪烁电路

在提交根目录创建 `blinker.sch`，以 XML 描述基于 555 定时器的非稳态 LED 闪烁原理图。评分只检查结构，不运行 EAGLE、ERC，也不验证逐引脚连接。

检查项目：

1. XML 格式正确。
2. 至少一个 `<part>` 的 deviceset 或 device 匹配不区分大小写的 `/555/`；提供的 `linear.lbr` 含符合要求的 `*555`。
3. 包含 R1、R2、C1、C2，以及 LED1 或 D1，名称不区分大小写。
4. 至少有一个 VCC 和一个 GND 电源元件：可使用 supply1/supply2 库中的 VCC/GND，或参考标号以 VCC/GND/SUP 开头。
5. `<sheet><nets>` 中至少有三个 `<net>`，典型为 VCC、GND、OUT，以及定时网络中的 THRES/DISCH。
6. R1/R2 的值应为电阻形式，如 `10k`、`100k`、`2.2M`；C1 应为电容形式，如 `10u`、`100n`、`47nF`；拒绝空值和 `?`。

提供 `linear.lbr`（EAGLE 7.7.0 的 *555）、`supply1.lbr`（VCC/GND/+V/+12V）、`rcl.lbr`（R-EU_、C-EU）和 `led.lbr`。无需将完整元件库嵌入原理图，评分读取 `<part>` 属性。

EAGLE 原理图骨架示例：

    <?xml version="1.0" encoding="utf-8"?>
    <!DOCTYPE eagle SYSTEM "eagle.dtd">
    <eagle version="7.7.0">
      <drawing>
        <settings>.../</settings>
        <grid .../>
        <layers>.../</layers>
        <schematic xreflabel="..." xrefpart="...">
          <libraries>.../</libraries>
          <attributes/> <variantdefs/> <classes>.../</classes>
          <parts>
            <part name="IC1" library="linear" deviceset="*555" device="N"/>
            <part name="R1"  library="rcl" deviceset="R-EU_" device="0207/10" value="10k"/>
            ...
          </parts>
          <sheets>
            <sheet>
              <plain/> <instances>.../</instances> <busses/>
              <nets>
                <net name="VCC" class="0"><segment>...</segment></net>
                ...
              </nets>
            </sheet>
          </sheets>
        </schematic>
      </drawing>
    </eagle>


文件通常只有数 KB；如果仅满足上述结构评分，可以省略 wires/instances。

真实 555 非稳态电路的频率近似为 `f = 1.44 / ((R1 + 2 R2) C1)`。目标可取 1–2 Hz；例如 R1=10k、R2=100k、C1=10u 时约为 0.68 Hz。
