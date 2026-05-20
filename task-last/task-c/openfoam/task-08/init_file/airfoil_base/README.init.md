# Task 8 airfoil_base init template

- Source: custom (blockMesh + spline)
- Purpose: 训练用可编辑缺口模板，保留关键参数 TODO_*，不是直接收敛的成品算例。
- Notes:
- 不使用预生成 polyMesh，改为 blockMeshDict + spline 骨架。- 当前 airfoil patch 为训练模板占位，需补全真实 NACA0012 拓扑。- 攻角、样条控制点、自由流速度均保留 TODO_*。
