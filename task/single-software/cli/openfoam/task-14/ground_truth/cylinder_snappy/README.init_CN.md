[English](README.init.md) | [简体中文](README.init_CN.md)

# 任务 14：snappy_base 初始化模板

- 来源：OpenFOAM-10/tutorials/mesh/snappyHexMesh/pipe + generated cylinder STL
- 用途：可编辑的训练模板，关键参数保留 `TODO_*` 占位符，尚不是可直接运行的收敛算例。

## 说明

- 已提供 `constant/triSurface/cylinder.stl`：直径 0.1 m、长度 0.01 m、中心为 (0.5, 0.5, 0)。
- `snappyHexMeshDict` 已指向所提供的 `cylinder.stl`。
- 层网格和细化级别保留 `TODO_*` 占位符。
