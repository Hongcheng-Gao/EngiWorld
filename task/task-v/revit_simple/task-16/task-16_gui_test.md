# task-16 GUI Test Report

Status: PASS-GUI

Test environment:
- Snapshot: Revit2025
- OS: Windows
- Host used during test: 124.174.35.96
- Final eval evidence: `/Users/leiyu/workspace/OSWorld/logs/gui-revit-simple/task-16/eval-final/20260602-033234/before_setup.png` and evaluator output `True`

Reproducible GUI workflow:

1. Launch Revit 2025 through the task config.
2. If Revit Home does not expose the full IFC open path, create a temporary new project, then use File -> Open -> IFC to open `C:\Users\user\Desktop\init.ifc`.
3. In the Level 1 plan, keep the seed floor slab as the building base.
4. Use Architecture -> Wall to draw a compact apartment layout with four room-bounded cells. A simple outer rectangle, one vertical partition, and one horizontal partition are sufficient; add another short wall segment if needed to give the export at least seven wall elements.
5. Use Architecture -> Door to place at least three hosted doors.
6. Use Architecture -> Window to place at least two hosted exterior windows.
7. Use Architecture -> Room to place four rooms in the new room-bounded cells.
8. Create a Room Schedule from View -> Schedules -> Schedule/Quantities, choose Rooms, and add the `Number` and `Name` fields.
9. In the schedule, edit the four new rooms' `Number` and `Name` fields to `Living`, `Bedroom`, `Bath`, and `Kitchen`.
10. Open File -> Export -> IFC.
11. Click Modify setup, go to Additional Content, enable Export only elements visible in view and Export rooms, areas and spaces in 3D views, then click OK.
12. Set the export filename to `C:\Users\user\Desktop\result.ifc` and click Export. If Revit asks to overwrite an existing file, confirm overwrite.
13. Run eval with `--skip-config --evaluate`.

Notes:
- The Room Schedule path reliably controlled the exported native room names; the passing IFC contained `Living`, `Bedroom`, `Bath`, and `Kitchen` as `IfcSpace` names.
- The passing IFC contained one building storey, sufficient walls/slab/doors/windows, and no `IfcBuildingElementProxy` entities.
- No task files, evaluator logic, instruction text, initial files, or ground truth files were modified.
