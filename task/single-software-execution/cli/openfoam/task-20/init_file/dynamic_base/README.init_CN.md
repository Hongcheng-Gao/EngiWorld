[English](README.init.md) | [简体中文](README.init_CN.md)

# 任务 20：dynamic_base 初始化模板

- 来源：OpenFOAM-10/tutorials/incompressible/pimpleFoam/laminar/offsetCylinder
- 用途：可编辑的训练模板，关键参数保留 `TODO_*` 占位符，尚不是可直接运行的收敛算例。

## 说明

- O-grid 网格包含内部圆柱，可用于所需的动网格场结构。
- `constant/dynamicMeshDict` 包含 `oscillatingRotatingMotion` 占位配置。
- `controlDict` 使用 `pimpleDyMFoam`，并保留时间步占位符。
