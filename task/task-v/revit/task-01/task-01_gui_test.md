# task-01 GUI Test Report

Status: PASS-GUI

Test environment:
- Snapshot: Revit2025
- OS: Windows
- Instance: i-yenf4o0x6ocva4h94bsv
- Host used during test: 124.174.110.244
- Final eval evidence: `/new_home/leiyu/workspace/OSWorld/logs/gui-revit-simple/task-01/eval3/result.json`

Reproducible GUI workflow:

1. Launch Revit 2025 through the task config and wait until the Revit Home screen is visible.
2. In Revit Home, click Models -> New, keep the default Imperial Multi-discipline template, choose Project, and click OK.
3. In the L1 floor plan, use Architecture -> Wall and draw a closed rectangular room footprint with four wall segments.
4. Use Architecture -> Floor. In sketch mode, pick the four wall boundary lines, then click Finish to create the floor slab.
5. Use Architecture -> Door and place a door hosted on the lower wall.
6. Use Architecture -> Window and place a fixed window hosted on the upper wall.
7. Use Architecture -> Room and click inside the enclosed rectangle to create a room.
8. Select the room tag, click Select Host, then edit the room properties:
   - Number: `Office 101`
   - Name: `Office 101`
9. Select the fixed window and open Edit Type. In Type Properties, uncheck Muntin Visibility.
10. Open Visibility/Graphic Overrides with shortcut `VG`. Search for `Generic Models`, uncheck the Generic Models category, and click OK. This hides the nested trim/muntin Generic Model subcomponents in the active view.
11. Open File -> Export -> IFC.
12. Click Modify setup, go to Additional Content, enable Export only elements visible in view, enable Export rooms, areas and spaces in 3D views, and click OK.
13. Set the export filename to `C:\Users\user\Desktop\result.ifc` and click Export. If Revit asks to overwrite an existing file, confirm overwrite.
14. Run eval with `--skip-config --evaluate`.

Notes:
- The first export failed because the default fixed window exported nested trim/muntin objects as `IfcBuildingElementProxy`.
- Hiding `Generic Models` in the active view and exporting only visible elements removed those proxy entities while preserving `IfcWindow`.
- Revit exports room Number as `IfcSpace.Name`, so the room Number also needed to be `Office 101` for the existing evaluator.
