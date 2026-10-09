[English](README.init.md) | [简体中文](README.init_CN.md)

# Task 8 airfoil_base 初始化模板

来源：自定义 blockMesh + spline。

用途：可编辑的训练模板，关键参数使用 `TODO_*` 占位，尚不是可直接运行并收敛的算例。

- 提供 blockMeshDict 和样条骨架，而非预先生成的 polyMesh。
- 翼型 patch 仍为占位，需完成实际 NACA0012 拓扑。
- 攻角、样条控制点和来流速度保留 `TODO_*` 占位。
