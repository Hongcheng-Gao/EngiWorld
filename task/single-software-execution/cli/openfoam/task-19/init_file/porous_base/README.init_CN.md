[English](README.init.md) | [简体中文](README.init_CN.md)

# 任务 19：porous_base 初始化模板

- 来源：OpenFOAM-10/tutorials/incompressible/simpleFoam/pipeCyclic + porousSimpleFoam reference
- 用途：可编辑的训练模板，关键参数保留 `TODO_*` 占位符，尚不是可直接运行的收敛算例。

## 说明

- 基线求解器为 OpenFOAM 10 中的 `porousSimpleFoam`。
- `constant/porosityProperties` 和 `system/topoSetDict` 已包含占位配置。
- 也可使用 `simpleFoam` 与 `fvOptions`（`explicitPorositySource`）。
