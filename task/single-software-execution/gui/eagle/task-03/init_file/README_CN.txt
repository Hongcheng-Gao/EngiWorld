[English](README.txt) | [简体中文](README_CN.txt)

# 配置 EAGLE 四层叠层

目标自上而下：L1 SIG 外层信号铜 35 μm；0.2 mm FR-4 半固化片；L2 GND 内平面铜 35 μm；1.065 mm FR-4 芯板；L3 PWR 内平面铜 35 μm；0.2 mm 半固化片；L16 SIG 外层信号铜 35 μm。

成品总厚度约 1.6 mm，FR-4 在 1 GHz 下 Dk 约 4.3。

在 EAGLE 板编辑器打开 `stackup_seed.brd`，进入 Tools → DRC，将两层改为 1/2/3/16 四层叠层，介质厚度为 0.200 / 1.065 / 0.200 mm。

制造下限：`mdWireWire`、`mdWirePad`、`mdWireVia`、`mdPadPad`、`mdPadVia`、`mdViaVia` 均至少 0.15 mm；`mdDrill` 至少 0.30 mm；`msWidth` 至少 0.15 mm。

保存为 `hspeed_4layer.brd`。
