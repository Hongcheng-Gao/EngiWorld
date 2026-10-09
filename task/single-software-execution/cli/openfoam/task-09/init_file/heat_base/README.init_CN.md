[English](README.init.md) | [简体中文](README.init_CN.md)

# 任务 9：heat_base 初始化模板

- 来源：custom (cavity-style rectangular conduction template)
- 用途：可编辑的训练模板，关键参数保留 `TODO_*` 占位符，尚不是可直接运行的收敛算例。

## 说明

- 几何结构为矩形平板导热模型，不是法兰楔形模型。
- `0/T` 和 `constant/physicalProperties` 保留温度和扩散系数占位符。
- 求解器为 `laplacianFoam`。
