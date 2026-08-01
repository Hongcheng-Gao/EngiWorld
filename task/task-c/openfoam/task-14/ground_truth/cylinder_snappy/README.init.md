# Task 14 snappy_base init template

- Source: /new_home/weiyipeng/OpenFOAM-10-master/tutorials/mesh/snappyHexMesh/pipe + generated cylinder STL
- Purpose: 训练用可编辑缺口模板，保留关键参数 TODO_*，不是直接收敛的成品算例。
- Notes:
- 已预生成 constant/triSurface/cylinder.stl（直径 0.1m，长度 0.01m，中心 (0.5,0.5,0)）。- snappyHexMeshDict 已指向 cylinder.stl，避免外部资源缺失。- 网格层数/细化等级保留 TODO_*。
