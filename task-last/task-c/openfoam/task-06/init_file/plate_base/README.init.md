# Task 6 plate_base init template

- Source: custom (plate boundary-layer topology)
- Purpose: 训练用可编辑缺口模板，保留关键参数 TODO_*，不是直接收敛的成品算例。
- Notes:
- blockMeshDict 底边拆分为 upstreamWall/plate/downstreamWall。- 平板无滑移边界在 0/U 的 plate patch。- 速度、黏度、时间步参数都保留 TODO_*。
