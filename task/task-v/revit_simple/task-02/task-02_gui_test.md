# task-02 GUI Test Report

Status: PASS-GUI

Test environment:
- Snapshot: Revit2025
- OS: Windows
- Instance: i-yenfb64wlccva4hfw5o3
- Host used during test: 124.174.110.140
- Final eval evidence: `/new_home/leiyu/workspace/OSWorld/logs/gui-revit-simple/task-02/eval/result.json`

Reproducible GUI workflow:

1. Launch Revit 2025 through the task config and wait until the Revit Home screen is visible.
2. Click Models -> New, keep the default Imperial Multi-discipline template, choose Project, and click OK.
3. In the L1 floor plan, use Architecture -> Wall and draw the outer rectangular suite with four wall segments.
4. Use Architecture -> Floor before drawing the partition. Pick only the four exterior walls as the floor boundary and finish the sketch.
5. Use Architecture -> Wall to draw one vertical interior partition between the two room bays.
6. Use Architecture -> Door and place one exterior door in each bay on the lower exterior wall.
7. Use Architecture -> Window and place exterior windows. Additional hosted windows on side or exterior walls are acceptable as long as at least two `IfcWindow` elements export.
8. Use Architecture -> Room & Area -> Room and place one room in each bay.
9. Create a room schedule using View -> Create -> Schedules -> Schedule/Quantities. Choose the Rooms category, then add the Number and Name fields.
10. In the room schedule, edit the rows so both Number and Name are set to:
    - `Office A`
    - `Office B`
11. Return to the L1 plan view. Open Visibility/Graphic Overrides with shortcut `VG`, search for `Generic Models`, uncheck the Generic Models category, and click OK.
12. Open File -> Export -> IFC.
13. Click Modify setup, go to Additional Content, enable Export only elements visible in view and Export rooms, areas and spaces in 3D views, then click OK.
14. Set the export filename to `C:\Users\user\Desktop\result.ifc` and click Export.
15. Run eval with `--skip-config --evaluate`.

Notes:
- The room schedule was the most reliable GUI path for editing Room Number and Room Name after placement.
- As in task-01, hiding `Generic Models` before IFC export avoids nested default window trim/muntin exporting as `IfcBuildingElementProxy`.
- The floor should be created before drawing the interior partition, or the partition may be picked into the floor sketch and create an invalid boundary.
