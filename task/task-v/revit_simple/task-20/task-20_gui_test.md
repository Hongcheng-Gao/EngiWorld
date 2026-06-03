# task-20 GUI Test Report

Status: PASS-GUI

Test environment:
- Snapshot: Revit2025
- OS: Windows
- Instance: i-yenhalkgzkxjd1vd5sky
- Host used during test: 124.174.121.91
- Final eval evidence: `/new_home/leiyu/workspace/OSWorld/logs/gui-revit-simple/task-20/eval2/20260601-212014/before_setup.png` and evaluator output `True`

Reproducible GUI workflow:

1. Launch Revit 2025 through the task config and wait for Revit Home.
2. Open the provided seed IFC with File -> Open -> IFC, then select `C:\Users\user\Desktop\init.ifc`. The normal Home Models -> Open dialog does not accept `.ifc`; the dedicated IFC entry is required.
3. In the imported Level 1 floor plan, use Architecture -> Wall to draw additional simple standard walls if needed.
4. Activate Architecture -> Wall, open the wall type selector in Properties, search for `storefront`, choose the `Storefront` curtain wall type, and draw a storefront curtain wall segment.
5. Use Architecture -> Room to place a room. If Revit reports that the seed boundary is not properly enclosed, add room separators or a small native room-bounding loop with Revit GUI tools, then place the room again.
6. Create a room schedule using View -> Create -> Schedules -> Schedule/Quantities. Choose the Rooms category and add the Number and Name fields.
7. Edit the room schedule so the target room Number and Name are `Retail`.
8. Select the placed room in the L1 view, scroll the Properties panel to IFC Parameters, and set `NameOverride` to `Retail`. In this imported IFC workflow, Revit exports `NameOverride` as `IfcSpace.Name`; without this step the old seed name can remain in `IfcSpace.Name`.
9. Return to the L1 model view. Open File -> Export -> IFC.
10. Set the export filename to `C:\Users\user\Desktop\result.ifc` and click Export.
11. Run eval with `--skip-config --evaluate`.

Notes:
- The exported IFC passed the task evaluator after setting the room IFC `NameOverride` field.
- The final exported IFC contained the required project/storey/space, walls, slab, door, curtain walls, no `IfcBuildingElementProxy`, unique GlobalIds, and an `IfcSpace.Name` containing `Retail`.
- No task files, evaluator logic, instruction text, initial files, or ground truth files were modified.
