# task-06 GUI Test Report

Status: PASS-GUI after task refinement

Test environment:
- Snapshot: Revit2025
- OS: Windows
- Host used during test: 124.174.35.96
- Final eval evidence: `/Users/leiyu/workspace/OSWorld/logs/gui-revit-simple-retest/task-06/eval-gui/20260602-124615`, evaluator output `True`

Reproducible GUI workflow:

1. Launch Revit through the task config.
2. From Revit Home, create a temporary blank project if needed, then use File -> Open -> IFC to open `C:\Users\user\Desktop\init.ifc`.
3. Keep the imported seed shell, floor slab, exterior door, and windows.
4. Create a Room Schedule from View -> Schedules -> Schedule/Quantities, choose Rooms, and add the `Number` and `Name` fields.
5. Edit the single room row in the schedule so both the room number and room name are `Reception`.
6. Return to the model view and open File -> Export -> IFC.
7. In Modify setup, enable room/space export from the Additional Content tab.
8. Export to `C:\Users\user\Desktop\result.ifc`, confirming overwrite if prompted.
9. Run eval with `--skip-config --evaluate`.

Notes:
- The refined task keeps stable seed geometry and requires a GUI room rename, because redraw/sketch operations against imported IFC were unreliable in this environment.
- The evaluator accepts the Revit IFC export convention where schedule-edited room names may be written to `IfcSpace.LongName`.

