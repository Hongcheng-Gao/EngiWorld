# task-05 GUI Test Report

Status: PASS-GUI

Test environment:
- Snapshot: Revit2025
- OS: Windows
- Instance: i-yenfmtl1j4wh2yras49p
- Host used during test: 124.174.99.204
- Final eval evidence: `/new_home/leiyu/workspace/OSWorld/logs/gui-revit-simple/task-05/eval/result.json`

Reproducible GUI workflow:

1. Launch Revit 2025 through the task config and wait until the Revit Home screen is visible.
2. Click Models -> New, keep the default Imperial Multi-discipline template, choose Project, and click OK.
3. In the L1 floor plan, use Architecture -> Wall and draw three standard perimeter walls: the back wall and the two side walls.
4. Activate Architecture -> Wall again, open the wall type selector in Properties, search for `Curtain`, choose the `Storefront` curtain wall type, and draw the front wall.
5. Use Architecture -> Floor. If picking the wall boundaries causes an intersecting-line sketch error at the curtain-wall joins, quit the sketch and redraw a simple interior rectangular floor boundary with the Line sketch tool, then click Finish.
6. Use Architecture -> Door and place one hosted door on a standard side wall.
7. Use Architecture -> Room and click inside the enclosed room to create one room.
8. Create a room schedule using View -> Create -> Schedules -> Schedule/Quantities. Choose the Rooms category and add the Number field.
9. In the room schedule, edit the room Number row to `Storefront`. Revit exports Room Number as `IfcSpace.Name`, which is the value checked by the evaluator.
10. Return to the L1 model view. Open File -> Export -> IFC.
11. Set the export filename to `C:\Users\user\Desktop\result.ifc` and click Export.
12. Run eval with `--skip-config --evaluate`.

Notes:
- The IFC export option is disabled while a schedule view is active. Switch back to the L1 model view before exporting.
- A full IFC export passed for this task; the storefront curtain wall did not introduce `IfcBuildingElementProxy` entities in this run.
- No task files, evaluator logic, instruction text, initial files, or ground truth files were modified.
