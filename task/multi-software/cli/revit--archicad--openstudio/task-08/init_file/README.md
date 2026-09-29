[English](README.md) | [简体中文](README_CN.md)

This directory contains the complete task-local Task-08 workflow: the two-storey
laboratory IFC seed, weather and workflow contracts, Revit 2025 bridge source and
compiled add-in, Archicad 27 IFC4 translator/launcher, and OpenStudio 3.10.0
converter/launcher. The OpenStudio launcher first runs
`extract_ifc_space_geometry.py` so model geometry and containment come from the
real `stage2.ifc`. Run `run_revit_stage.ps1`, `run_archicad_stage.ps1`, then
`run_openstudio_stage.ps1` in that order on the pinned Windows snapshot.
