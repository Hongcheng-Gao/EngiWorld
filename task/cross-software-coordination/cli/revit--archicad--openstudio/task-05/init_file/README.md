[English](README.md) | [简体中文](README_CN.md)

This directory contains the immutable task-05 IFC4 seed and its executable native workflow contract.

The seed has two 10.0 m by 7.0 m storeys. Its interior room footprint is 9.8 m by 6.8 m: two Ground Floor rooms separated by one internal wall and one Level 2 room. The Revit stage removes only that Ground Floor partition, creates one upper room-separation line, and creates a real opening in the original Level 2 slab. The seed itself contains no opening, so the workflow deliberately says create rather than retain.

Official version references used for this task:

- Revit 2025 API and IFC export: https://help.autodesk.com/view/RVT/2025/ENU/?guid=Revit_API_Revit_API_Developers_Guide_html
- Revit 2025 `NewOpening(Element, CurveArray, Boolean)`: https://www.revitapidocs.com/2025/ab1718f9-45fb-b3d3-827e-32ff81cf929c.htm
- Archicad 27 IFC: https://help.graphisoft.com/AC/27/INT/_AC27_Help/121_IFC/121_IFC-4.htm
- Archicad JSON Interface: https://archicadapi.graphisoft.com/JSONInterfaceDocumentation/
- OpenStudio 3.10.0: https://github.com/NatLabRockies/OpenStudio/releases/tag/v3.10.0
- EnergyPlus 25.1 SQLite output: https://bigladdersoftware.com/epx/docs/25-1/output-details-and-examples/eplusout-sql.html
