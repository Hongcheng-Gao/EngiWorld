[English](README.md) | [简体中文](README_CN.md)

This directory contains the Task-03 clinic seed and its complete task-local native workflow. The Revit 2025 bridge preserves the imported clinic shell and creates a single waiting-to-records room boundary. Archicad 27 inspects and preserves the boundary state that the native Revit export actually contains, without synthesizing unsupported second-level relationships. OpenStudio 3.10.0 and its bundled EnergyPlus 25.1.0 generate and simulate the downstream energy model.

The benchmark uploads the compiled bridge, its add-in manifest, the IFC translator, all three launchers, the Ruby converter, the immutable seed/specification/weather inputs, and no shared mutable workflow helpers.
