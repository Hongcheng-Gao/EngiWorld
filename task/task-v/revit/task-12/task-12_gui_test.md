# task-12 GUI Test Report

Status: PASS-GUI

Test environment:
- Snapshot: Revit2025
- OS: Windows
- Host used during test: 124.174.35.96
- Final eval evidence: `/Users/leiyu/workspace/OSWorld/logs/gui-revit-simple/task-12/eval-final/20260602-051057/before_setup.png` and evaluator output `True`

Reproducible GUI workflow:

1. Launch Revit 2025 through the task config.
2. If Revit Home does not expose the full IFC open path, create a temporary new project, then use File -> Open -> IFC to open `C:\Users\user\Desktop\init.ifc`.
3. In the Level 1 plan, keep the seed floor slab as the building base.
4. Use Architecture -> Wall to draw a corridor-and-room plan:
   - Draw an outer rectangle.
   - Draw one horizontal partition to separate the corridor from the rooms.
   - Draw two vertical partitions above the corridor to create three rooms.
5. Use Architecture -> Door to place three doors between the rooms and corridor, plus one exterior door for the corridor.
6. Use Architecture -> Room to place one room in each of the three upper rooms and one room in the corridor.
7. Create a Room Schedule from View -> Schedules -> Schedule/Quantities, choose Rooms, and add the `Number` and `Name` fields.
8. In the schedule, edit the four new rooms' `Number` and `Name` fields to `Room 1`, `Room 2`, `Room 3`, and `Corridor`.
9. Open File -> Export -> IFC.
10. Click Modify setup, go to Additional Content, enable Export rooms, areas and spaces in 3D views, then click OK.
11. Set the export filename to `C:\Users\user\Desktop\result.ifc` and click Export. If Revit asks to overwrite an existing file, confirm overwrite.
12. Run eval with `--skip-config --evaluate`.

Notes:
- The Room Schedule path reliably controlled exported native `IfcSpace` names.
- The passing IFC contained `Corridor`, `Room 1`, `Room 2`, and `Room 3`, one building storey, sufficient walls/slab/doors, and no `IfcBuildingElementProxy` entities.
- No task files, evaluator logic, instruction text, initial files, or ground truth files were modified.
