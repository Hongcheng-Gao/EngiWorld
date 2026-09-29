[English](README.md) | [简体中文](README_CN.md)

本目录包含完整的 Task-08 任务内工作流：两层实验楼 IFC 初始模型、天气与工作流约定、Revit 2025 桥接源码和已编译插件、Archicad 27 IFC4 转换器及启动器，以及 OpenStudio 3.10.0 转换程序及启动器。OpenStudio 启动器先执行 `extract_ifc_space_geometry.py`，从实际的 `stage2.ifc` 获取模型几何与包含关系。请在指定 Windows 快照中依次运行 `run_revit_stage.ps1`、`run_archicad_stage.ps1`、`run_openstudio_stage.ps1`。
