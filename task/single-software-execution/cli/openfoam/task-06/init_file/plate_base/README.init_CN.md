[English](README.init.md) | [简体中文](README.init_CN.md)

# 任务 6：plate_base 初始化模板

- 来源：custom (plate boundary-layer topology)
- 用途：可编辑的训练模板，关键参数保留 `TODO_*` 占位符，尚不是可直接运行的收敛算例。

## 说明

- `blockMeshDict` 的底边分为 `upstreamWall`、`plate` 和 `downstreamWall`。
- 平板无滑移边界位于 `0/U` 的 `plate` 边界区。
- 速度、黏度和时间步参数保留 `TODO_*` 占位符。
