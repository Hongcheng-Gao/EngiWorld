[English](README.md) | [简体中文](README_CN.md)

# Task-09 初始化包

本目录包含 task-09 培训中心条形建筑初始模型和独立可执行工作流。按顺序运行三个 Windows 阶段：

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_revit_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_archicad_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_openstudio_stage.ps1
```

包内包含专用 Revit 2025 桥接 DLL/清单、Archicad 27 IFC4 转换器和 JEMI 启动器、IFC 几何提取器及 OpenStudio 3.10 转换程序，不依赖 `_common` 或其他任务的状态。每次运行应从这些文件开始；收集产物后清理安装的 Revit 插件和生成文件。
