# task-19 GUI Test Report

Status: PASS-GUI

Test environment:
- Snapshot: Revit2025
- OS: Windows
- Instance host used during test: 124.174.35.96
- Final eval evidence: `/Users/leiyu/workspace/OSWorld/logs/gui-revit-simple/task-19/eval-final/20260602-011526/before_setup.png` and evaluator output `True`

Reproducible GUI workflow:

1. Launch Revit 2025 through the task config and wait for Revit Home or the desktop.
2. Open the provided seed IFC with File -> Open -> IFC, selecting `C:\Users\user\Desktop\init.ifc`.
3. In the Level 1 plan, keep the existing seed walls, lower floor slab, and room geometry.
4. Create or open a Level 2 floor plan from the Project Browser. If a Level 2 floor plan is missing, use View -> Plan Views -> Floor Plan and enable Level 2.
5. In the Level 2 plan, use Architecture -> Wall to create four simple upper-level walls above the seed footprint.
6. Use Architecture -> Floor on Level 2. In floor boundary sketch mode, use the `LI` line shortcut to draw a closed rectangular boundary, then click Finish Edit Mode to create the upper floor slab.
7. Return to Level 1 and use Architecture -> Stair, not Shaft Opening. Draw a simple straight run from Level 1 to Level 2, then click Finish Edit Mode.
8. In Level 2, use Architecture -> Room to place the upper room inside the upper enclosure. Select the room tag, click Select Host, scroll to IFC Parameters in Properties, and set `NameOverride` to `Bedroom`.
9. In Level 1, if the original imported seed room keeps its old IFC name, use Architecture -> Room Separator to draw a small closed separator rectangle inside the lower level.
10. Use Architecture -> Room to place a new room inside that separator rectangle. Select the room tag, click Select Host, scroll to IFC Parameters in Properties, and set `NameOverride` to `Living`.
11. Open File -> Export -> IFC.
12. Set the export filename to `C:\Users\user\Desktop\result.ifc` and click Export. If Revit asks to overwrite an existing file, confirm overwrite.
13. Run eval with `--skip-config --evaluate`.

Notes:
- The first export failed because the stair was accidentally created through an Opening/Shaft workflow and did not export as `IfcStair`.
- The seed room kept its original IFC name `Seed Room`; adding a separate GUI-created, room-bounded lower room named `Living` produced the required `IfcSpace` without changing the task files.
- The passing IFC contained `Living` and `Bedroom` spaces, two storeys, four walls, two slabs, one stair, and no `IfcBuildingElementProxy` entities.
- No task files, evaluator logic, instruction text, initial files, or ground truth files were modified.
