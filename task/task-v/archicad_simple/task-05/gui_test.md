# GUI Test Report

Result: PASS-GUI

Task JSON: `task-05.json`
Test log: `/new_home/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-05/eval/result.json`

## Reproducible GUI Procedure

1. Work in an `ArchiCAD-27` Windows instance and create a simple two-storey building with real BIM elements.
2. Use real Wall elements to form a compact two-storey shell.
3. Add at least two Slab elements, one for the lower floor and one for the upper floor.
4. Place a real Stair element connecting the levels.
5. Place at least two Door elements and two Window elements.
6. Add Zones with Zone Name and Zone No. set to:
   - `GROUND ROOM`
   - `UPPER ROOM`
7. If reusing a larger draft model, use Archicad's native Resize command from the GUI:
   - Select the relevant 3D elements.
   - Open Resize.
   - Disable `Define graphically`.
   - Keep X/Y ratio fields neutral and set the percentage field to the required uniform scale.
8. Save from Floor Plan, not selected-only 3D export, so Zones export as `IfcSpace`.
9. Save As `C:\Users\user\Desktop\result.ifc`.
10. Select `IFC Files (*.ifc)` and `IFC4 Design Transfer View-based Export`, then save.
11. Run eval with `--skip-config --evaluate`.

## Notes

The passing diagnostic export had overall shaped span about `7.97 m x 4.66 m x 7.18 m`. Exporting from selected-only 3D omitted Zones, so the final IFC must be saved from Floor Plan with visible elements on all stories.
