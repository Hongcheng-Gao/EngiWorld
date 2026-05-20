# Task 19 porous_base init template

- Source: /new_home/weiyipeng/OpenFOAM-10-master/tutorials/incompressible/simpleFoam/pipeCyclic + porousSimpleFoam reference
- Purpose: 训练用可编辑缺口模板，保留关键参数 TODO_*，不是直接收敛的成品算例。
- Notes:
- 主线采用 porousSimpleFoam（OpenFOAM-10 可用）。- 已加入 constant/porosityProperties 与 system/topoSetDict 占位。- 兼容建议：可改用 simpleFoam + fvOptions(explicitPorositySource)。
