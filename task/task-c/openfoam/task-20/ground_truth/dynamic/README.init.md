# Task 20 dynamic_base init template

- Source: /new_home/weiyipeng/OpenFOAM-10-master/tutorials/incompressible/pimpleFoam/laminar/offsetCylinder
- Purpose: 训练用可编辑缺口模板，保留关键参数 TODO_*，不是直接收敛的成品算例。
- Notes:
- 使用带内部圆柱的 O-grid 基础网格，满足动网格目标场景。
- 新增 constant/dynamicMeshDict，采用 oscillatingRotatingMotion 占位。
- controlDict 已切换为 pimpleDyMFoam，并保留时间参数占位。
