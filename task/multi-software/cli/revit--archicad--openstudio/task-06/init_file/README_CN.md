[English](README.md) | [简体中文](README_CN.md)

# Task-06 可执行输入

这些文件构成 task-06 车间初始模型的 Windows 工作流。在桌面目录依次运行 `run_revit_stage.ps1`、`run_archicad_stage.ps1`、`run_openstudio_stage.ps1`。不要复用其他任务的文件或运行状态。

Revit 桥接程序固定使用 Revit 2025，将导入的一个房间替换为三个原生房间，同时保留真实的六柱布局、四面墙、楼板、空间容器、结构 GlobalId 和世界坐标。初始模型没有 IFC grid 实体。Archicad 阶段使用 build 6000 的 IFC Command Server/JEMI 接口和提供的 IFC4 转换器。OpenStudio 阶段需要 3.10.0 及其 EnergyPlus 25.1.0 运行时。
