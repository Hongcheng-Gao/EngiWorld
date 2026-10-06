[English](README.md) | [简体中文](README_CN.md)

## TSinflow (`Mod_AmbWind=2`)

两个交错布置的 NREL 5-MW 风机沿主流向相距 3D，横向偏移 30 m；使用一个 TurbSim 湍流风场作为入流（`Mod_AmbWind=2`）。

在各风机下游 1R（0.5D）处输出速度，参见 `OutDist`。

此算例用于测试。进行实际模拟时：

- 遵循 [FAST.Farm 建模指南](https://openfast.readthedocs.io/en/dev/source/user/fast.farm/ModelGuidance.html)。
- 使用符合实际的风机间距。
- 考虑增加径向输出位置（`OutRadii`）。
- 延长模拟时间，必要时同步调整 `NumPlanes` 和 `NX_Low`。
- 通常应在离转子更远的位置布置更多输出截面。
