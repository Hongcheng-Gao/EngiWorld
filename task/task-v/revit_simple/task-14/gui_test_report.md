# task-14 GUI Test Report

Status: PASS-GUI

Test environment:
- Snapshot: Revit2025
- OS: Windows
- Host used during test: 124.174.35.96
- Final eval evidence: `/Users/leiyu/workspace/OSWorld/logs/gui-revit-simple/task-14/eval-final/20260602-041122/before_setup.png` and evaluator output `True`

Reproducible GUI workflow:

1. Launch Revit 2025 through the task config.
2. If Revit Home does not expose the full IFC open path, create a temporary new project, then use File -> Open -> IFC to open `C:\Users\user\Desktop\init.ifc`.
3. In the Level 1 plan, keep the seed floor slab as the building base.
4. Use Architecture -> Wall to draw a simple rectangular one-storey hall.
5. Use Architecture -> Door to place one hosted door in the hall wall.
6. Use Architecture -> Room to place one room inside the hall.
7. Create a Room Schedule from View -> Schedules -> Schedule/Quantities, choose Rooms, and add the `Number` and `Name` fields.
8. In the schedule, edit the new room's `Number` and `Name` to `Beam Hall`.
9. Return to Level 1, open the Structure tab, and use Structure -> Column to place at least two structural columns near the top of the hall.
10. Use Structure -> Beam to draw at least two beams near the top of the hall.
11. Open File -> Export -> IFC.
12. Click Modify setup, go to Additional Content, enable Export rooms, areas and spaces in 3D views, then click OK. Do not rely on visible-only export if Revit warns that structural elements are not visible in the active plan.
13. Set the export filename to `C:\Users\user\Desktop\result.ifc` and click Export. If Revit asks to overwrite an existing file, confirm overwrite.
14. Run eval with `--skip-config --evaluate`.

Notes:
- Revit may warn that newly created structural columns or beams are not visible in the active plan because of view range or visibility settings; they can still export correctly as IFC structural elements.
- The passing IFC contained `Beam Hall`, one building storey, sufficient walls/slab/door, two `IfcColumn` entities, two `IfcBeam` entities, and no `IfcBuildingElementProxy` entities.
- No task files, evaluator logic, instruction text, initial files, or ground truth files were modified.
