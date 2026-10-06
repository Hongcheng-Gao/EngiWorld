[English](README.md) | [简体中文](README_CN.md)

# Task-06 executable inputs

These files form the task-specific Windows workflow for the task-06 workshop
seed. Run `run_revit_stage.ps1`, `run_archicad_stage.ps1`, and
`run_openstudio_stage.ps1` in that order from the Desktop. Do not reuse files or
runtime state from another task.

The Revit bridge is pinned to Revit 2025 and replaces the seed's one imported
room with three native rooms while preserving the actual six-column layout,
four walls, slab, spatial containers, structural GlobalIds, and world
coordinates. The seed has no IFC grid entities. The Archicad stage uses build
6000's IFC Command Server/JEMI interface and the supplied IFC4 translator. The
OpenStudio stage requires OpenStudio 3.10.0 and its EnergyPlus 25.1.0 runtime.
