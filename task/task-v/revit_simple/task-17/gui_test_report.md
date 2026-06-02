# task-17 GUI Test Report

Status: PASS-GUI

Test environment:
- Snapshot: Revit2025
- OS: Windows
- Host used during test: 124.174.35.96
- Final eval evidence: `/Users/leiyu/workspace/OSWorld/logs/gui-revit-simple/task-17/eval-final/20260602-030432/before_setup.png` and evaluator output `True`

Reproducible GUI workflow:

1. Launch Revit 2025 through the task config.
2. If Revit Home does not expose the full IFC open path, create a temporary new project, then use File -> Open -> IFC to open `C:\Users\user\Desktop\init.ifc`.
3. In the Level 1 plan, keep the seed floor slab as the building base.
4. Use the Wall tool, or the `WA` shortcut, to draw a compact one-storey classroom/storage layout with perimeter walls and an interior partition.
5. Use the Door tool, or `DR`, to place at least two hosted doors.
6. Use the Window tool, or `WN`, to place at least two hosted exterior windows.
7. Use the Room tool, or `RM`, to place one room in each new room-bounded area.
8. Create a Room Schedule from View -> Schedules -> Schedule/Quantities, choose Rooms, and add the `Number` and `Name` fields.
9. In the schedule, edit one new room's `Number` and `Name` to `Classroom`, and edit the other new room's `Number` and `Name` to `Storage`.
10. Open Visibility/Graphic Overrides from View -> Graphics. Search for `Generic Models`, uncheck the Generic Models category, and click OK.
11. Open File -> Export -> IFC.
12. Click Modify setup, go to Additional Content, enable Export only elements visible in view and Export rooms, areas and spaces in 3D views, then click OK.
13. Set the export filename to `C:\Users\user\Desktop\result.ifc` and click Export. If Revit asks to overwrite an existing file, confirm overwrite.
14. Run eval with `--skip-config --evaluate`.

Notes:
- Editing only IFC `NameOverride` on native Revit rooms did not change the exported `IfcSpace.Name`; the Room Schedule path exposed the native `Number` and `Name` fields reliably.
- Hiding `Generic Models` in the active view and exporting only visible elements removed proxy entities while preserving the required walls, slab, doors, windows, and rooms.
- The passing IFC contained `Classroom` and `Storage` spaces, one building storey, sufficient walls/slab/doors/windows, and no `IfcBuildingElementProxy` entities.
- No task files, evaluator logic, instruction text, initial files, or ground truth files were modified.
