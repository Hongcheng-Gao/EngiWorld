# task-18 GUI Test Report

Status: PASS-GUI

Test environment:
- Snapshot: Revit2025
- OS: Windows
- Host used during test: 124.174.35.96
- Final eval evidence: `/Users/leiyu/workspace/OSWorld/logs/gui-revit-simple/task-18/eval-final/20260602-020602/before_setup.png` and evaluator output `True`

Reproducible GUI workflow:

1. Launch Revit 2025 through the task config and open the provided seed IFC from `C:\Users\user\Desktop\init.ifc`.
2. In the Level 1 plan, keep the seed geometry as a starting reference.
3. Use the Revit Wall tool, or the `WA` shortcut, to draw a small rectangular clinic pair with four perimeter walls and one interior partition.
4. Use the Door tool, or `DR`, to place two or more hosted doors. One exterior door per room is sufficient; an interior partition door is also acceptable.
5. Use the Window tool, or `WN`, to place at least two hosted exterior windows.
6. Use the Room tool, or `RM`, to place one room in each clinic bay.
7. For each new room tag, click Select Host and edit the room IFC Parameters in Properties:
   - Set `NameOverride` for one room to `Waiting`.
   - Set `NameOverride` for the other room to `Exam`.
8. Open Visibility/Graphic Overrides with shortcut `VG`. Search for `Generic Models`, uncheck the Generic Models category, and click OK.
9. Open File -> Export -> IFC.
10. Click Modify setup, go to Additional Content, enable Export only elements visible in view and Export rooms, areas and spaces in 3D views, then click OK.
11. Set the export filename to `C:\Users\user\Desktop\result.ifc` and click Export. If Revit asks to overwrite an existing file, confirm overwrite.
12. Run eval with `--skip-config --evaluate`.

Notes:
- A full IFC export contained `IfcBuildingElementProxy` entities from nested default door/window subcomponents.
- Hiding `Generic Models` in the active view and exporting only visible elements removed the proxy entities while preserving the required walls, slab, doors, windows, and rooms.
- The passing IFC contained `Waiting` and `Exam` spaces, at least one storey, sufficient walls/slabs/doors/windows, and no `IfcBuildingElementProxy` entities.
- No task files, evaluator logic, instruction text, initial files, or ground truth files were modified.
