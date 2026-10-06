[English](README.md) | [简体中文](README_CN.md)

# Task-09 init package

This directory is a self-contained task-09 training-centre bar-building seed and executable workflow. Run the three pinned Windows stages in order:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_revit_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_archicad_stage.ps1
powershell -ExecutionPolicy Bypass -File C:\Users\user\Desktop\run_openstudio_stage.ps1
```

The package includes its task-specific Revit 2025 bridge DLL/manifest, Archicad 27 IFC4 translator and JEMI launcher, IFC geometry extractor, and OpenStudio 3.10 converter. It does not depend on `_common` or another task's state. Each fresh task run must start from these files and must clean the installed Revit add-in plus generated work products after artifacts are collected.
