# GUI Test Report

Result: PASS-GUI

Task JSON: `task-08.json`
Test log: `/new_home/leiyu/workspace/OSWorld/logs/gui-archicad-simple/task-08/eval/result.json`

## Reproducible GUI Procedure

1. Run the task config to upload and open `init.ifc` in Archicad.
2. Accept the IFC import/library dialog with the default Embedded Library option.
3. In Floor Plan, use the Wall Tool to draw one real internal wall splitting the original `OPEN STUDIO` room into two rooms.
4. Use the Door Tool to place doors so both rooms have door elements.
5. Use the Window Tool to place two real window elements in the exterior wall.
6. Select the Zone Tool and set both Zone Name and Zone No. to `STUDIO`.
7. Draw a rectangular zone over the left room and click inside it to place the zone stamp.
8. Set both Zone Name and Zone No. to `MEETING`.
9. Draw a rectangular zone over the right room and click inside it to place the zone stamp.
10. Use File > Save As, save to `C:\Users\user\Desktop\result.ifc`.
11. Select `IFC Files (*.ifc)` and `IFC4 Design Transfer View-based Export`, then save.
12. Run eval with `--skip-config --evaluate`.

## Notes

The passing result keeps the imported slab and exterior shell, adds a real internal wall, and exports the two Archicad Zones as IFC4 `IfcSpace` entries named `STUDIO` and `MEETING`.
